from fastapi.testclient import TestClient
import pytest

from app.main import app
from scripts.import_game_logs import persist_logs
from test_game_log_persistence import sample_frame


@pytest.fixture
def client(postgres_db, monkeypatch):
    import app.player_games as routes
    monkeypatch.setattr(routes, "engine", postgres_db)
    return TestClient(app)


def test_profile(client):
    response = client.get("/api/v1/players/1")
    assert response.status_code == 200
    assert response.json()["full_name"] == "Stephen Curry"


def test_empty_and_unknown(client):
    assert client.get("/api/v1/players/2/games").json()["games"] == []
    assert client.get("/api/v1/players/999/games").status_code == 404
    assert client.get("/api/v1/players/999").status_code == 404


def test_recent_window_is_chronological(client, postgres_db):
    import pandas as pd
    frame = pd.concat([sample_frame()] * 3, ignore_index=True)
    frame["Game_ID"] = ["0022500001", "0022500002", "0022500003"]
    frame["GAME_DATE"] = ["OCT 21, 2025", "OCT 23, 2025", "OCT 25, 2025"]
    frame.loc[1, "MATCHUP"] = "GSW vs. LAL"
    persist_logs(frame, 201939, "2025-26", postgres_db)
    response = client.get("/api/v1/players/1/games?limit=2&season=2025-26")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert [g["game_date"] for g in data["games"]] == ["2025-10-23", "2025-10-25"]
    assert [g["is_home"] for g in data["games"]] == [True, False]
    assert all(g["opponent_abbreviation"] == "LAL" for g in data["games"])
    assert data["games"][0]["minutes"] == 32.5
    assert client.get("/api/v1/players/1/games?offset=2&limit=2").json()["games"][0]["game_date"] == "2025-10-21"
    assert client.get("/api/v1/players/1/games?season=2024-25").json()["total"] == 0


@pytest.mark.parametrize("query", ["limit=0", "limit=201", "offset=-1", "season=bad", "season=2025-99"])
def test_bounds(client, query):
    assert client.get(f"/api/v1/players/1/games?{query}").status_code == 422
