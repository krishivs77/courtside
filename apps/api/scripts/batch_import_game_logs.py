"""Sequential, resumable NBA ingestion. Checkpoints contain no database credentials."""
import argparse
import fcntl
from functools import wraps
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Callable

from nba_api.stats.static import players as nba_players
from sqlalchemy import select

from app.db import engine
from app.models import Game, Player, PlayerGameStats, Season
from scripts.import_game_logs import UpstreamUnavailable, fetch_logs, persist_logs, validate_season


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_checkpoint(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Replace on the same filesystem; interruption never leaves half-written JSON.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as file:
            temporary = file.name
            json.dump(state, file, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def load_checkpoint(path: Path) -> dict:
    state = json.loads(path.read_text())
    if state.get("version") != 1 or not isinstance(state.get("targets"), list) or not isinstance(state.get("players"), dict):
        raise ValueError("Invalid checkpoint format")
    validate_season(state.get("season", ""))
    targets = state["targets"]
    if not targets or any(type(value) is not int or value < 1 for value in targets) or len(set(targets)) != len(targets):
        raise ValueError("Invalid checkpoint targets")
    for key, outcome in state["players"].items():
        if key not in {str(value) for value in targets} or not isinstance(outcome, dict):
            raise ValueError("Invalid checkpoint player outcome")
        if outcome.get("status") not in {"success", "empty", "error"}:
            raise ValueError("Invalid checkpoint status")
        if type(outcome.get("attempts")) is not int or outcome["attempts"] < 1:
            raise ValueError("Invalid checkpoint attempts")
        if outcome["status"] in {"success", "empty"}:
            ids = outcome.get("source_game_ids")
            if not isinstance(ids, list) or any(not isinstance(value, str) for value in ids):
                raise ValueError("Invalid checkpoint source game IDs")
            if (outcome["status"] == "success" and not ids) or (outcome["status"] == "empty" and ids):
                raise ValueError("Invalid checkpoint source game IDs")
    return state


def stored_game_ids(player_id: int, season: str, db_engine=engine) -> set[str]:
    with db_engine.connect() as connection:
        return set(connection.scalars(
            select(Game.external_id).select_from(PlayerGameStats)
            .join(Game, Game.id == PlayerGameStats.game_id)
            .join(Player, Player.id == PlayerGameStats.player_id)
            .join(Season, Season.id == Game.season_id)
            .where(Player.external_id == str(player_id), Season.start_year == int(season[:4]),
                   Season.season_type == "Regular Season")
        ))


def checkpoint_lock(function):
    @wraps(function)
    def locked(player_ids, season, checkpoint, **kwargs):
        checkpoint = Path(checkpoint)
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        with checkpoint.with_suffix(checkpoint.suffix + ".lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("Another importer is using this checkpoint") from exc
            return function(player_ids, season, checkpoint, **kwargs)
    return locked


@checkpoint_lock
def run_batch(
    player_ids: list[int], season: str, checkpoint: Path, *,
    fetch: Callable = fetch_logs, persist: Callable = persist_logs,
    sleep: Callable = time.sleep, delay: float = 1.0, retries: int = 2,
    refresh: bool = False, max_consecutive_failures: int = 3,
    cohort_source: str = "explicit NBA IDs", stored_ids: Callable = stored_game_ids,
) -> dict:
    validate_season(season)
    if delay < 0 or not 0 <= retries <= 5 or max_consecutive_failures < 1:
        raise ValueError("Invalid delay, retry or circuit-breaker configuration")
    targets = list(dict.fromkeys(player_ids))
    if not targets or any(not isinstance(value, int) or value < 1 for value in targets):
        raise ValueError("Provide positive NBA player IDs")
    if checkpoint.exists():
        state = load_checkpoint(checkpoint)
        if state["season"] != season or state["targets"] != targets:
            raise ValueError("Season or cohort differs from checkpoint; use a separate checkpoint")
    else:
        state = {"version": 1, "season": season, "season_type": "Regular Season",
                 "created_at": utc_now(), "cohort_source": cohort_source, "targets": targets, "players": {}}
        save_checkpoint(checkpoint, state)
    failures = 0
    for index, player in enumerate(targets):
        key = str(player)
        previous = state["players"].get(key, {})
        if not refresh and previous.get("status") in {"success", "empty"}:
            if stored_ids(player, season) == set(previous["source_game_ids"]):
                continue
            print(f"NBA player {player}: checkpoint differs from database; refetching", flush=True)
        print(f"[{index + 1}/{len(targets)}] NBA player {player}", flush=True)
        outcome = {"status": "error", "attempts": previous.get("attempts", 0), "updated_at": utc_now()}
        upstream_failed = False
        for attempt in range(retries + 1):
            outcome["attempts"] += 1
            try:
                frame = fetch(player, season)
            except UpstreamUnavailable:
                if attempt < retries:
                    sleep(max(delay, 1.0) * 2 ** attempt)
                    continue
                outcome["error"] = "NBA upstream unavailable after bounded retries"
                upstream_failed = True
                break
            try:
                if frame.empty:
                    outcome.update(status="empty", source_game_ids=[], imported=0)
                else:
                    source_ids = sorted(set(str(value) for value in frame["Game_ID"]))
                    count = persist(frame, player, season)
                    outcome.update(status="success", source_game_ids=source_ids, imported=count)
            except Exception as exc:
                # Do not retry validation/database failures or write credentials to state.
                outcome["error"] = f"Import rejected ({type(exc).__name__}); inspect data/schema before retrying"
            break
        outcome["updated_at"] = utc_now()
        state["players"][key] = outcome
        state["updated_at"] = utc_now()
        save_checkpoint(checkpoint, state)
        print(f"  {outcome['status']}: {outcome.get('imported', 0)} rows", flush=True)
        failures = failures + 1 if upstream_failed else 0
        if failures >= max_consecutive_failures:
            print("Stopping after consecutive upstream failures; rerun to resume.", flush=True)
            break
        sleep(delay)
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", default="2025-26")
    parser.add_argument("--players", type=int, nargs="+", help="Explicit NBA external IDs")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--limit", type=int, help="Limit initial active-player cohort; frozen on resume")
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--refresh", action="store_true", help="Refetch successful and empty responses")
    args = parser.parse_args()
    if args.checkpoint.exists() and args.players is None:
        targets = load_checkpoint(args.checkpoint)["targets"]
    elif args.players:
        targets = args.players
    else:
        if args.limit is not None and args.limit < 1:
            parser.error("--limit must be positive")
        targets = sorted(player["id"] for player in nba_players.get_active_players())
        if args.limit:
            targets = targets[:args.limit]
    # Fail preflight rather than making upstream requests for unseeded identities.
    with engine.connect() as connection:
        known = set(connection.scalars(select(Player.external_id).where(Player.external_id.in_([str(i) for i in targets]))))
    missing = [player for player in targets if str(player) not in known]
    if missing:
        parser.error(f"{len(missing)} target identities are not seeded; run scripts.seed_players first")
    state = run_batch(targets, args.season, args.checkpoint, delay=args.delay, retries=args.retries, refresh=args.refresh,
                      cohort_source="explicit NBA IDs" if args.players else "nba_api bundled current active-player snapshot (not season roster)")
    done = all(state["players"].get(str(player), {}).get("status") in {"success", "empty"} for player in targets)
    print(f"Checkpoint: {args.checkpoint}; all targets attempted successfully: {done}")
    return 0 if done else 1


if __name__ == "__main__":
    raise SystemExit(main())
