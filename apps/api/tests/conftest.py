import os
import uuid

import pytest
from sqlalchemy import text

from app.db import engine
from app.models import Base, Player, Team


@pytest.fixture
def postgres_db():
    """Use an isolated schema; never modify or delete application tables."""
    if os.getenv("RUN_POSTGRES_TESTS") != "1":
        pytest.skip("Set RUN_POSTGRES_TESTS=1 to run isolated PostgreSQL integration tests")
    schema = "test_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    db = engine.execution_options(schema_translate_map={None: schema})
    try:
        Base.metadata.create_all(db)
        with db.begin() as conn:
            conn.execute(Team.__table__.insert(), [
                {"id": 1, "external_id": "gsw", "name": "Warriors", "abbreviation": "GSW"},
                {"id": 2, "external_id": "lal", "name": "Lakers", "abbreviation": "LAL"},
            ])
            conn.execute(Player.__table__.insert(), [
                {"id": 1, "external_id": "201939", "full_name": "Stephen Curry"},
                {"id": 2, "external_id": "empty", "full_name": "Empty History"},
            ])
        yield db
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
