"""Player detail and bounded, chronologically ordered historical performances."""
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.orm import aliased

from app.db import engine
from app.models import Game, Player, PlayerGameStats, Season, Team

router = APIRouter(prefix="/api/v1/players", tags=["players"])


class PlayerProfile(BaseModel):
    id: int
    external_id: str
    full_name: str
    position: str | None
    current_team_id: int | None


class PlayerGame(BaseModel):
    game_id: int
    external_id: str
    game_date: date
    season: str
    season_type: str
    opponent_abbreviation: str
    opponent_name: str
    team_abbreviation: str
    is_home: bool
    minutes: float | None
    points: int
    rebounds: int
    assists: int
    fgm: int
    fga: int
    three_pm: int
    three_pa: int
    source: str | None
    retrieved_at: datetime | None


class PlayerGamesResponse(BaseModel):
    player: PlayerProfile
    games: list[PlayerGame]
    total: int
    limit: int
    offset: int


def find_player(connection, player_id: int):
    player = connection.execute(select(Player.__table__).where(Player.id == player_id)).mappings().one_or_none()
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return dict(player)


@router.get("/{player_id}", response_model=PlayerProfile)
def get_player(player_id: int):
    with engine.connect() as connection:
        return find_player(connection, player_id)


@router.get("/{player_id}/games", response_model=PlayerGamesResponse)
def get_player_games(
    player_id: int,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100000),
    season: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
):
    if season and int(season[-2:]) != (int(season[:4]) + 1) % 100:
        raise HTTPException(status_code=422, detail="Season must use consecutive years")
    stat = PlayerGameStats
    opponent = aliased(Team)
    player_team = aliased(Team)
    game_date = func.coalesce(Game.game_date, cast(func.timezone("UTC", Game.scheduled_at), Date))
    conditions = [stat.player_id == player_id]
    if season:
        conditions.extend([Season.start_year == int(season[:4]), Season.season_type == "Regular Season"])
    with engine.connect() as connection:
        player = find_player(connection, player_id)
        total = connection.scalar(
            select(func.count()).select_from(stat).join(Game, Game.id == stat.game_id)
            .join(Season, Season.id == Game.season_id).where(*conditions)
        )
        statement = (
            select(
                Game.id.label("game_id"), Game.external_id, game_date.label("game_date"),
                Season.start_year, Season.season_type,
                opponent.abbreviation.label("opponent_abbreviation"), opponent.name.label("opponent_name"),
                player_team.abbreviation.label("team_abbreviation"),
                (stat.team_id == Game.home_team_id).label("is_home"),
                stat.minutes, stat.points, stat.rebounds, stat.assists,
                stat.fgm, stat.fga, stat.three_pm, stat.three_pa, stat.source, stat.retrieved_at,
            ).select_from(stat).join(Game, Game.id == stat.game_id)
            .join(Season, Season.id == Game.season_id)
            .join(player_team, player_team.id == stat.team_id)
            .join(opponent, opponent.id == case((stat.team_id == Game.home_team_id, Game.away_team_id), else_=Game.home_team_id))
            .where(*conditions).order_by(game_date.desc(), Game.id.desc()).limit(limit).offset(offset)
        )
        rows = connection.execute(statement).mappings().all()
        games = []
        for row in reversed(rows):
            values = dict(row)
            year = values.pop("start_year")
            values["season"] = f"{year}-{(year + 1) % 100:02d}"
            games.append(values)
        return {"player": player, "games": games, "total": total, "limit": limit, "offset": offset}
