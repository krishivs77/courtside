import argparse
import math
import re
from datetime import datetime, time, timezone

import pandas as pd
from nba_api.stats.endpoints import PlayerGameLog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db import engine
from app.models import Game, Player, PlayerGameStats, Season, Team


def get_minutes(value) -> float | None:
    if pd.isna(value):
        return None
    if isinstance(value, str) and ":" in value:
        minutes, seconds = value.split(":", 1)
        if not minutes.isdigit() or not seconds.isdigit() or not 0 <= int(seconds) < 60:
            raise ValueError(f"Invalid minutes: {value}")
        value = int(minutes) + int(seconds) / 60
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"Invalid minutes: {value}")
    return result


def get_stat(row, field: str) -> int:
    value = row.get(field)
    if pd.isna(value):
        raise ValueError(f"Missing statistic: {field}")
    number = float(value)
    if not math.isfinite(number) or number < 0 or not number.is_integer():
        raise ValueError(f"Invalid statistic {field}: {value}")
    return int(number)


def parse_matchup(matchup: str) -> tuple[str, str, str]:
    match = re.fullmatch(r"([A-Z]{2,3}) (vs\. |@ )([A-Z]{2,3})", matchup.strip())
    if not match or match[1] == match[3]:
        raise ValueError(f"Unknown matchup: {matchup}")
    player, marker, opponent = match.groups()
    return (player, opponent, player) if marker == "vs. " else (opponent, player, player)



class UpstreamUnavailable(RuntimeError):
    """A retryable NBA transport or response failure (before database writes)."""


def validate_season(season: str) -> None:
    if not re.fullmatch(r"\d{4}-\d{2}", season) or int(season[-2:]) != (int(season[:4]) + 1) % 100:
        raise ValueError("Season must use consecutive years, e.g. 2025-26")


def fetch_logs(player_nba_id: int, season: str) -> pd.DataFrame:
    validate_season(season)
    try:
        response = PlayerGameLog(
            player_id=player_nba_id, season=season,
            season_type_all_star="Regular Season", timeout=30,
        )
        return response.get_data_frames()[0]
    except Exception as exc:
        raise UpstreamUnavailable("NBA upstream unavailable; database unchanged. Retry later.") from exc


def import_logs(player_nba_id: int, season: str) -> int:
    print(f"Fetching player {player_nba_id}, season {season}...", flush=True)
    return persist_logs(fetch_logs(player_nba_id, season), player_nba_id, season)


def persist_logs(frame: pd.DataFrame, player_nba_id: int, season: str, db_engine=engine) -> int:
    """Atomically validate and upsert one player-season response (no inferred zeros)."""
    validate_season(season)
    if frame.empty:
        raise ValueError("No game logs returned. Database unchanged.")
    retrieved_at = datetime.now(timezone.utc)
    with db_engine.begin() as conn:
        player_id = conn.execute(
            select(Player.id).where(
                Player.external_id == str(player_nba_id)
            )
        ).scalar_one_or_none()

        if player_id is None:
            raise RuntimeError("Player not found. Seed players first.")

        teams = {
            row.abbreviation: row.id
            for row in conn.execute(
                select(Team.abbreviation, Team.id)
            ).all()
        }

        start_year = int(season.split("-")[0])

        season_stmt = insert(Season).values(
            start_year=start_year,
            season_type="Regular Season",
        ).on_conflict_do_update(
            index_elements=["start_year", "season_type"],
            set_={"season_type": "Regular Season"},
        ).returning(Season.id)

        season_id = conn.execute(season_stmt).scalar_one()

        imported = 0

        for _, row in frame.iterrows():
            matchup = str(row["MATCHUP"])

            home_abbr, away_abbr, player_abbr = parse_matchup(matchup)
            if any(abbr not in teams for abbr in (home_abbr, away_abbr)):
                raise ValueError(f"Unknown team in matchup: {matchup}")
            if "Player_ID" in row and str(row["Player_ID"]) != str(player_nba_id):
                raise ValueError("Response contains a different player")
            home_id = teams[home_abbr.strip()]
            away_id = teams[away_abbr.strip()]
            team_id = teams[player_abbr.strip()]

            game_date = pd.to_datetime(row["GAME_DATE"]).date()

            start_year = int(season[:4])
            if not (datetime(start_year, 7, 1).date() <= game_date < datetime(start_year + 1, 10, 1).date()):
                raise ValueError(f"Game date outside season: {game_date}")
            external_id = str(row["Game_ID"])
            if not re.fullmatch(rf"002{start_year % 100:02d}\d{{5}}", external_id):
                raise ValueError(f"Invalid regular-season game ID: {external_id}")

            # Date-only placeholder, NOT verified tipoff time.
            game_timestamp = datetime.combine(
                game_date, time.min, tzinfo=timezone.utc
            )

            game_stmt = insert(Game).values(
                external_id=external_id,
                season_id=season_id,
                home_team_id=home_id,
                away_team_id=away_id,
                scheduled_at=game_timestamp,
                status="final",
                game_date=game_date,
                source="nba_api.PlayerGameLog",
                timestamp_precision="date",
            )

            game_stmt = game_stmt.on_conflict_do_update(
                index_elements=["external_id"],
                set_={
                    "season_id": game_stmt.excluded.season_id,
                    "game_date": game_stmt.excluded.game_date,
                    "source": game_stmt.excluded.source,
                    "status": "final",
                    "home_team_id": game_stmt.excluded.home_team_id,
                    "away_team_id": game_stmt.excluded.away_team_id,
                },
            ).returning(Game.id)

            game_id = conn.execute(game_stmt).scalar_one()

            values = {
                "game_id": game_id,
                "player_id": player_id,
                "team_id": team_id,
                "source": "nba_api.PlayerGameLog",
                "retrieved_at": retrieved_at,
                "minutes": get_minutes(row["MIN"]),
                "points": get_stat(row, "PTS"),
                "rebounds": get_stat(row, "REB"),
                "assists": get_stat(row, "AST"),
                "steals": get_stat(row, "STL"),
                "blocks": get_stat(row, "BLK"),
                "turnovers": get_stat(row, "TOV"),
                "fgm": get_stat(row, "FGM"),
                "fga": get_stat(row, "FGA"),
                "three_pm": get_stat(row, "FG3M"),
                "three_pa": get_stat(row, "FG3A"),
                "ftm": get_stat(row, "FTM"),
                "fta": get_stat(row, "FTA"),
            }

            for made, attempted in (("fgm", "fga"), ("three_pm", "three_pa"), ("ftm", "fta")):
                if values[made] > values[attempted]:
                    raise ValueError(f"Made shots exceed attempts: {made}")
            stat_stmt = insert(PlayerGameStats).values(**values)

            stat_stmt = stat_stmt.on_conflict_do_update(
                index_elements=["game_id", "player_id"],
                set_={
                    key: getattr(stat_stmt.excluded, key)
                    for key in values
                    if key not in {"game_id", "player_id"}
                },
            )

            conn.execute(stat_stmt)
            imported += 1

    print(f"Imported {imported} games successfully.")
    return imported


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--player", type=int, required=True)
    parser.add_argument("--season", default="2025-26")
    args = parser.parse_args()

    import_logs(args.player, args.season)
