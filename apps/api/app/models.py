from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Float,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    abbreviation: Mapped[str] = mapped_column(String(8))
    conference: Mapped[str | None] = mapped_column(String(20))


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True
    )
    full_name: Mapped[str] = mapped_column(String(150))
    position: Mapped[str | None] = mapped_column(String(20))
    current_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id")
    )


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(primary_key=True)
    start_year: Mapped[int] = mapped_column(Integer)
    season_type: Mapped[str] = mapped_column(String(30))

    __table_args__ = (
        UniqueConstraint("start_year", "season_type"),
    )


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True
    )
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id")
    )
    home_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id")
    )
    away_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id")
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    status: Mapped[str] = mapped_column(
        String(30), default="scheduled"
    )
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)


class PlayerGameStats(Base):
    __tablename__ = "player_game_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id"), index=True
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"), index=True
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id")
    )

    minutes: Mapped[float | None] = mapped_column(Float)
    points: Mapped[int] = mapped_column(Integer, default=0)
    rebounds: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)
    steals: Mapped[int] = mapped_column(Integer, default=0)
    blocks: Mapped[int] = mapped_column(Integer, default=0)
    turnovers: Mapped[int] = mapped_column(Integer, default=0)

    fgm: Mapped[int] = mapped_column(Integer, default=0)
    fga: Mapped[int] = mapped_column(Integer, default=0)
    three_pm: Mapped[int] = mapped_column(Integer, default=0)
    three_pa: Mapped[int] = mapped_column(Integer, default=0)
    ftm: Mapped[int] = mapped_column(Integer, default=0)
    fta: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("game_id", "player_id"),
    )
