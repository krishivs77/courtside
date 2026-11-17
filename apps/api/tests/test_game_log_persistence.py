from datetime import date

import pandas as pd
import pytest
from sqlalchemy import func, select

from app.models import Game, PlayerGameStats, Season
from scripts.import_game_logs import persist_logs


def sample_frame():
    # Synthetic fixture only; never loaded into the application schema.
    return pd.DataFrame([{
        "Game_ID": "0022500001", "Player_ID": 201939,
        "MATCHUP": "GSW @ LAL", "GAME_DATE": "OCT 21, 2025", "MIN": "32:30",
        **{key: 2 for key in ("PTS", "REB", "AST", "STL", "BLK", "TOV", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA")},
    }])


def test_repeat_import_updates_without_duplicates(postgres_db):
    frame = sample_frame()
    assert persist_logs(frame, 201939, "2025-26", postgres_db) == 1
    frame.loc[0, "PTS"] = 30
    persist_logs(frame, 201939, "2025-26", postgres_db)
    with postgres_db.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(Game)) == 1
        assert conn.scalar(select(func.count()).select_from(PlayerGameStats)) == 1
        game = conn.execute(select(Game.__table__)).mappings().one()
        assert (game["home_team_id"], game["away_team_id"]) == (2, 1)
        assert game["game_date"] == date(2025, 10, 21)
        assert game["timestamp_precision"] == "date"
        stat = conn.execute(select(PlayerGameStats.__table__)).mappings().one()
        assert stat["team_id"] == 1
        assert stat["points"] == 30
        assert stat["retrieved_at"] is not None


def test_invalid_later_row_rolls_back_entire_import(postgres_db):
    frame = pd.concat([sample_frame(), sample_frame()], ignore_index=True)
    frame.loc[1, "Game_ID"] = "0022500002"
    frame.loc[1, "PTS"] = float("nan")
    with pytest.raises(ValueError, match="PTS"):
        persist_logs(frame, 201939, "2025-26", postgres_db)
    with postgres_db.connect() as conn:
        for model in (Game, PlayerGameStats, Season):
            assert conn.scalar(select(func.count()).select_from(model)) == 0


def test_extended_2019_season_accepts_august_bubble_game(postgres_db):
    frame = sample_frame()
    frame.loc[0, "Game_ID"] = "0021900001"
    frame.loc[0, "GAME_DATE"] = "AUG 01, 2020"
    assert persist_logs(frame, 201939, "2019-20", postgres_db) == 1
