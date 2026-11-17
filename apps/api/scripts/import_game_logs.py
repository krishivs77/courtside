import argparse
from datetime import datetime, time, timezone

import pandas as pd
from nba_api.stats.endpoints import PlayerGameLog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db import engine
from app.models import Game, Player, PlayerGameStats, Season, Team


def get_minutes(value):
    if pd.isna(value):
        return None
    if isinstance(value, str) and ":" in value:
        minutes, seconds = value.split(":", 1)
        return int(minutes) + float(seconds) / 60
    return float(value)


def get_stat(row, field):
    value = row[field]
    return 0 if pd.isna(value) else int(value)


def import_logs(player_nba_id, season):
    print(f"Fetching player {player_nba_id}, season {season}...")

    response = PlayerGameLog(
        player_id=player_nba_id,
        season=season,
        season_type_all_star="Regular Season",
        timeout=30,
    )

    frame = response.get_data_frames()[0]

    if frame.empty:
        raise RuntimeError(
            "No game logs returned. Database unchanged."
        )

    with engine.begin() as conn:
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

            if " vs. " in matchup:
                home_abbr, away_abbr = matchup.split(" vs. ")
                player_abbr = home_abbr
            elif " @ " in matchup:
                away_abbr, home_abbr = matchup.split(" @ ")
                player_abbr = away_abbr
            else:
                raise ValueError(f"Unknown matchup: {matchup}")

            home_id = teams[home_abbr.strip()]
            away_id = teams[away_abbr.strip()]
            team_id = teams[player_abbr.strip()]

            game_date = pd.to_datetime(row["GAME_DATE"]).date()

            # Date-only placeholder, NOT verified tipoff time.
            game_timestamp = datetime.combine(
                game_date, time.min, tzinfo=timezone.utc
            )

            game_stmt = insert(Game).values(
                external_id=str(row["Game_ID"]),
                season_id=season_id,
                home_team_id=home_id,
                away_team_id=away_id,
                scheduled_at=game_timestamp,
                status="final",
            )

            game_stmt = game_stmt.on_conflict_do_update(
                index_elements=["external_id"],
                set_={
                    "season_id": game_stmt.excluded.season_id,
                    "home_team_id": game_stmt.excluded.home_team_id,
                    "away_team_id": game_stmt.excluded.away_team_id,
                },
            ).returning(Game.id)

            game_id = conn.execute(game_stmt).scalar_one()

            values = {
                "game_id": game_id,
                "player_id": player_id,
                "team_id": team_id,
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

            stat_stmt = insert(PlayerGameStats).values(**values)

            stat_stmt = stat_stmt.on_conflict_do_update(
                constraint="player_game_stats_game_id_player_id_key",
                set_={
                    key: getattr(stat_stmt.excluded, key)
                    for key in values
                    if key not in {"game_id", "player_id"}
                },
            )

            conn.execute(stat_stmt)
            imported += 1

    print(f"Imported {imported} games successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--player", type=int, required=True)
    parser.add_argument("--season", default="2025-26")
    args = parser.parse_args()

    import_logs(args.player, args.season)
