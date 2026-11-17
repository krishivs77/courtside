"""Report stored data quality and reconciliation with the latest observed responses."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from sqlalchemy import select

from app.db import engine
from app.models import Game, Player, PlayerGameStats, Season
from scripts.batch_import_game_logs import load_checkpoint, save_checkpoint
from scripts.import_game_logs import validate_season


def quality_report(season: str, checkpoint: dict | None = None, db_engine=engine) -> dict:
    validate_season(season)
    if checkpoint and checkpoint["season"] != season:
        raise ValueError("Report season differs from checkpoint")
    with db_engine.connect() as connection:
        names = {row.external_id: row.full_name for row in connection.execute(select(Player.external_id, Player.full_name))}
        rows = connection.execute(
            select(Player.external_id, Player.full_name, Game.external_id.label("external_game_id"),
                   Game.game_date, Game.home_team_id, Game.away_team_id,
                   PlayerGameStats.__table__)
            .select_from(PlayerGameStats).join(Player, Player.id == PlayerGameStats.player_id)
            .join(Game, Game.id == PlayerGameStats.game_id).join(Season, Season.id == Game.season_id)
            .where(Season.start_year == int(season[:4]), Season.season_type == "Regular Season")
        ).mappings().all()
    grouped = {}
    for row in rows:
        key = row["external_id"]
        grouped.setdefault(key, []).append(row)
    outcomes = checkpoint.get("players", {}) if checkpoint else {}
    targets = [str(value) for value in checkpoint["targets"]] if checkpoint else []
    players = []
    for key in sorted(set(grouped) | set(targets)):
        stats = grouped.get(key, [])
        outcome = outcomes.get(key, {})
        stored_ids = {row["external_game_id"] for row in stats}
        observed_ids = set(outcome.get("source_game_ids", []))
        observed = outcome.get("status") in {"success", "empty"}
        dates = [row["game_date"] for row in stats if row["game_date"] is not None]
        invalid = 0
        for row in stats:
            counts = [row[field] for field in ("points", "rebounds", "assists", "steals", "blocks", "turnovers", "fgm", "fga", "three_pm", "three_pa", "ftm", "fta")]
            if (any(value < 0 for value in counts)
                or any(row[made] > row[attempted] for made, attempted in (("fgm", "fga"), ("three_pm", "three_pa"), ("ftm", "fta")))
                or (row["minutes"] is not None and (not math.isfinite(row["minutes"]) or row["minutes"] < 0))
                or row["team_id"] not in (row["home_team_id"], row["away_team_id"])):
                invalid += 1
        players.append({
            "external_id": key, "name": names.get(key),
            "targeted": key in targets, "status": outcome.get("status", "pending" if key in targets else "untracked"),
            "stored_appearances": len(stats), "first_date": min(dates).isoformat() if dates else None,
            "last_date": max(dates).isoformat() if dates else None,
            "missing_minutes": sum(row["minutes"] is None for row in stats),
            "missing_game_dates": sum(row["game_date"] is None for row in stats),
            "missing_provenance": sum(not row["source"] or row["retrieved_at"] is None for row in stats),
            "invalid_stat_rows": invalid,
            "observed_source_games": len(observed_ids) if observed else None,
            "missing_source_game_ids": sorted(observed_ids - stored_ids) if observed else None,
            "unexpected_stored_game_ids": sorted(stored_ids - observed_ids) if observed else None,
            "source_reconciled": stored_ids == observed_ids if observed else None,
        })
    summary = {status: sum(row["targeted"] and row["status"] == status for row in players) for status in ("success", "empty", "error", "pending")}
    summary.update(targets=len(targets), stored_players=len(grouped), stored_appearances=len(rows),
                   missing_minutes=sum(row["missing_minutes"] for row in players),
                   invalid_stat_rows=sum(row["invalid_stat_rows"] for row in players),
                   reconciliation_mismatches=sum(row["source_reconciled"] is False for row in players))
    return {"season": season, "season_type": "Regular Season", "generated_at": datetime.now(timezone.utc).isoformat(),
            "cohort_source": checkpoint.get("cohort_source", "explicit NBA IDs") if checkpoint else None,
            "independent_completeness_verified": False,
            "interpretation": "Reconciliation compares stored IDs with the last observed response only. Empty responses do not certify zero appearances; active-player metadata is not a season roster.",
            "summary": summary, "players": players}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", default="2025-26")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and args.checkpoint and args.output.resolve() == args.checkpoint.resolve():
        parser.error("Report output must differ from the checkpoint path")
    state = load_checkpoint(args.checkpoint) if args.checkpoint else None
    report = quality_report(args.season, state)
    if args.output:
        save_checkpoint(args.output, report)
        print(json.dumps(report["summary"], indent=2))
    else:
        print(json.dumps(report, indent=2))
    summary = report["summary"]
    return 1 if summary["error"] or summary["pending"] or summary["invalid_stat_rows"] or summary["reconciliation_mismatches"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
