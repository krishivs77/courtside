from scripts.ingestion_quality import quality_report
from scripts.import_game_logs import persist_logs
from test_game_log_persistence import sample_frame


def test_report_reconciles_source_ids_and_missing_minutes(postgres_db):
    from sqlalchemy import update
    from app.models import PlayerGameStats
    persist_logs(sample_frame(), 201939, "2025-26", postgres_db)
    with postgres_db.begin() as conn:
        conn.execute(update(PlayerGameStats).values(minutes=None))
    checkpoint = {"season": "2025-26", "targets": [201939, 99], "players": {
        "201939": {"status": "success", "source_game_ids": ["0022500001", "0022500002"]},
        "99": {"status": "empty", "source_game_ids": []},
    }}
    report = quality_report("2025-26", checkpoint, postgres_db)
    assert report["summary"]["stored_appearances"] == 1
    assert report["summary"]["pending"] == 0
    assert report["summary"]["empty"] == 1
    curry = next(row for row in report["players"] if row["external_id"] == "201939")
    assert curry["missing_minutes"] == 1
    assert curry["missing_source_game_ids"] == ["0022500002"]
    assert curry["unexpected_stored_game_ids"] == []
    assert curry["source_reconciled"] is False
    assert report["independent_completeness_verified"] is False


def test_report_without_checkpoint_does_not_claim_completeness(postgres_db):
    report = quality_report("2025-26", db_engine=postgres_db)
    assert report["summary"]["stored_appearances"] == 0
    assert report["summary"]["pending"] == 0
    assert report["players"] == []


def test_report_flags_nonfinite_minutes(postgres_db):
    from sqlalchemy import update
    from app.models import PlayerGameStats
    persist_logs(sample_frame(), 201939, "2025-26", postgres_db)
    with postgres_db.begin() as conn:
        conn.execute(update(PlayerGameStats).values(minutes=float("inf")))
    report = quality_report("2025-26", db_engine=postgres_db)
    assert report["summary"]["invalid_stat_rows"] == 1


def test_stored_id_lookup_is_scoped_by_player_and_season(postgres_db):
    from scripts.batch_import_game_logs import stored_game_ids
    persist_logs(sample_frame(), 201939, "2025-26", postgres_db)
    assert stored_game_ids(201939, "2025-26", postgres_db) == {"0022500001"}
    assert stored_game_ids(201939, "2024-25", postgres_db) == set()
    assert stored_game_ids(999999, "2025-26", postgres_db) == set()
