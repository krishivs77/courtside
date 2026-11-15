from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db import check_database, engine
from app.models import Team


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
