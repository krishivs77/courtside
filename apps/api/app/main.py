from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from app.db import check_database


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
