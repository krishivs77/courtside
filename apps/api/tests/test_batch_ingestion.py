from pathlib import Path

import pandas as pd
import pytest

from scripts.batch_import_game_logs import run_batch as _run_batch


def run_batch(*args, **kwargs):
    kwargs.setdefault("stored_ids", lambda *args: {"0022500001"})
    return _run_batch(*args, **kwargs)
from scripts.import_game_logs import UpstreamUnavailable


def test_retries_then_resume_skips_success(tmp_path):
    calls = []
    def fetch(player, season):
        calls.append(player)
        if len(calls) == 1:
            raise UpstreamUnavailable("offline")
        return pd.DataFrame([{"Game_ID": "0022500001"}])
    saved = []
    state = tmp_path / "batch.json"
    result = run_batch([201939], "2025-26", state, fetch=fetch,
                       persist=lambda frame, player, season: saved.append(player) or 1,
                       sleep=lambda seconds: None, delay=0)
    assert result["players"]["201939"]["status"] == "success"
    assert calls == [201939, 201939]
    run_batch([201939], "2025-26", state, fetch=fetch,
              persist=lambda *args: pytest.fail("must not repeat"), sleep=lambda _: None)
    assert len(calls) == 2
    assert saved == [201939]


def test_failure_empty_and_continuation(tmp_path):
    def fetch(player, season):
        if player == 1:
            raise UpstreamUnavailable("offline")
        return pd.DataFrame()
    result = run_batch([1, 2], "2025-26", tmp_path / "batch.json", fetch=fetch,
                       persist=lambda *args: pytest.fail("no empty persistence"),
                       sleep=lambda _: None, delay=0, retries=1)
    assert result["players"]["1"]["status"] == "error"
    assert result["players"]["2"]["status"] == "empty"
    assert result["players"]["1"]["attempts"] == 2


def test_checkpoint_rejects_different_season_or_cohort(tmp_path):
    path = tmp_path / "batch.json"
    run_batch([1], "2025-26", path, fetch=lambda *args: pd.DataFrame(), sleep=lambda _: None, delay=0)
    with pytest.raises(ValueError, match="checkpoint"):
        run_batch([1], "2024-25", path)
    with pytest.raises(ValueError, match="checkpoint"):
        run_batch([2], "2025-26", path)


def test_interruption_saves_completed_players(tmp_path):
    def fetch(player, season):
        if player == 2:
            raise KeyboardInterrupt()
        return pd.DataFrame([{"Game_ID": "0022500001"}])
    path = tmp_path / "batch.json"
    with pytest.raises(KeyboardInterrupt):
        run_batch([1, 2], "2025-26", path, fetch=fetch, persist=lambda *args: 1, sleep=lambda _: None, delay=0)
    import json
    assert json.loads(path.read_text())["players"]["1"]["status"] == "success"


def test_circuit_breaker_leaves_remaining_players_pending(tmp_path):
    calls = []
    def fetch(player, season):
        calls.append(player)
        raise UpstreamUnavailable("offline")
    state = run_batch([1, 2, 3, 4], "2025-26", tmp_path / "batch.json", fetch=fetch,
                      sleep=lambda _: None, delay=0, retries=0)
    assert calls == [1, 2, 3]
    assert "4" not in state["players"]


def test_validation_failure_is_not_retried_and_refresh_refetches_empty(tmp_path):
    calls = []
    def fetch(player, season):
        calls.append(player)
        return pd.DataFrame([{"Game_ID": "0022500001"}])
    def reject(*args):
        raise ValueError("bad stats")
    path = tmp_path / "batch.json"
    state = run_batch([1], "2025-26", path, fetch=fetch, persist=reject, sleep=lambda _: None, delay=0)
    assert state["players"]["1"]["status"] == "error"
    assert calls == [1]
    state = run_batch([1], "2025-26", path, fetch=lambda *args: pd.DataFrame(), sleep=lambda _: None, delay=0)
    assert state["players"]["1"]["status"] == "empty"
    state = run_batch([1], "2025-26", path, fetch=fetch, persist=lambda *args: 1, refresh=True, sleep=lambda _: None, delay=0)
    assert state["players"]["1"]["status"] == "success"


def test_corrupt_checkpoint_is_rejected(tmp_path):
    import json
    path = tmp_path / "batch.json"
    path.write_text(json.dumps({"version": 1, "season": "2025-26", "targets": [1],
                                "players": {"1": {"status": "success"}}}))
    with pytest.raises(ValueError, match="checkpoint"):
        run_batch([1], "2025-26", path)



def test_resume_reimports_missing_database_records(tmp_path):
    path = tmp_path / "batch.json"
    fetch = lambda *args: pd.DataFrame([{"Game_ID": "0022500001"}])
    run_batch([1], "2025-26", path, fetch=fetch, persist=lambda *args: 1, sleep=lambda _: None, delay=0)
    persisted = []
    run_batch([1], "2025-26", path, fetch=fetch,
              persist=lambda *args: persisted.append(1) or 1,
              stored_ids=lambda *args: set(), sleep=lambda _: None, delay=0)
    assert persisted == [1]
