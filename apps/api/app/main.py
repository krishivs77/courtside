from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db import check_database, engine
from app.models import Player, Team


app = FastAPI(
    title="COURTSIDE API",
    description="NBA analytics and predictive modeling API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "courtside-api",
        "version": "0.1.0",
    }


@app.get("/ready")
def readiness():
    try:
        if check_database():
            return {
                "status": "ready",
                "database": "connected",
            }
    except SQLAlchemyError:
        pass

    raise HTTPException(
        status_code=503,
        detail="Database unavailable",
    )


@app.get("/api/v1/teams")
def get_teams():
    with engine.connect() as connection:
        result = connection.execute(
            select(
                Team.id,
                Team.external_id,
                Team.name,
                Team.abbreviation,
                Team.conference,
            ).order_by(Team.name)
        )

        return [
            {
                "id": row.id,
                "external_id": row.external_id,
                "name": row.name,
                "abbreviation": row.abbreviation,
                "conference": row.conference,
            }
            for row in result
        ]



@app.get("/api/v1/players")
def search_players(
    search: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
):
    query = search.strip()

    if len(query) < 2:
        raise HTTPException(
            status_code=422,
            detail="Search must contain at least two characters",
        )

    with engine.connect() as connection:
        result = connection.execute(
            select(
                Player.id,
                Player.external_id,
                Player.full_name,
                Player.position,
                Player.current_team_id,
            )
            .where(Player.full_name.ilike(f"%{query}%"))
            .order_by(Player.full_name)
            .limit(limit)
        )

        return [
            {
                "id": row.id,
                "external_id": row.external_id,
                "full_name": row.full_name,
                "position": row.position,
                "current_team_id": row.current_team_id,
            }
            for row in result
        ]


from app.player_games import router as player_router

app.include_router(player_router)
