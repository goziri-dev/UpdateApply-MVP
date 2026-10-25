"""Catalog / ingest / daily run entrypoints.

Run from ``server/``:

```bash
uv run updateapply-catalog seed-boards
uv run updateapply-catalog import-directory --download
uv run updateapply-catalog ingest
uv run updateapply-catalog daily
```
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlmodel import Session, select

from app.core.database import engine
from app.models.company_board import CompanyBoard
from app.services.ats_ingest import AtsIngestService
from app.services.board_directory import (
    DEFAULT_DIRECTORY_PATH,
    DIRECTORY_CSV_URL,
    download_directory_csv,
    load_directory_rows,
    upsert_directory_boards,
)
from app.services.board_seed import (
    DEFAULT_SEED_PATH,
    load_seed_file,
    upsert_company_boards,
)
from app.services.daily_job_run import run_daily
from app.services.job_match import backfill_embeddings, backfill_locations
from app.services.notify_matches import notify_all_users


def cmd_seed_boards(args: argparse.Namespace) -> int:
    path = Path(args.file) if args.file else DEFAULT_SEED_PATH
    rows = load_seed_file(path)
    with Session(engine) as session:
        result = upsert_company_boards(session, rows, source="seed")
    print(
        f"seed {path}: total={result.total_rows} "
        f"inserted={result.inserted} updated={result.updated} "
        f"skipped_bad={result.skipped_bad}"
    )
    for err in result.errors:
        print(f"  bad row: {err}", file=sys.stderr)
    return 1 if result.skipped_bad and not (result.inserted or result.updated) else 0


def cmd_import_directory(args: argparse.Namespace) -> int:
    """Full ATS Company Directory → company_board (CC-BY-4.0). Does not ingest."""
    path = Path(args.file) if args.file else DEFAULT_DIRECTORY_PATH
    if args.download or not path.is_file():
        print(f"downloading directory CSV → {path}")
        print(f"  source: {DIRECTORY_CSV_URL}")
        path = download_directory_csv(path)
    rows = load_directory_rows(path)
    with Session(engine) as session:
        result = upsert_directory_boards(session, rows)
    print(
        f"import-directory {path}: total={result.total_rows} "
        f"inserted={result.inserted} updated={result.updated} "
        f"skipped_vendor={result.skipped_vendor} skipped_bad={result.skipped_bad}"
    )
    print(
        "Attribution: ATS Company Directory by LastRound / fyrosofttech, "
        "CC-BY-4.0 — see data/ATTRIBUTION-ats-company-directory.md"
    )
    print("Jobs are not fetched here; run ingest or daily next.")
    for err in result.errors[:20]:
        print(f"  bad row: {err}", file=sys.stderr)
    if len(result.errors) > 20:
        print(f"  … {len(result.errors) - 20} more", file=sys.stderr)
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    with Session(engine) as session:
        board_ids = None
        if args.slug:
            boards = list(
                session.exec(
                    select(CompanyBoard).where(
                        CompanyBoard.slug == args.slug,
                        CompanyBoard.status == "active",
                    )
                ).all()
            )
            if not boards:
                print(
                    f"no active company_board with slug={args.slug!r}",
                    file=sys.stderr,
                )
                return 1
            board_ids = [b.id for b in boards]

        with AtsIngestService(session) as ingest:
            result = ingest.run(board_ids=board_ids)

    print(
        "ingest complete: "
        f"attempted={result.boards_attempted} ok={result.boards_ok} "
        f"failed={result.boards_failed} quarantined={result.boards_quarantined} "
        f"upserted={result.postings_upserted} "
        f"descriptions_written={result.descriptions_written} "
        f"descriptions_skipped={result.descriptions_skipped} "
        f"deactivated={result.deactivated}"
    )
    for stats in result.board_stats:
        status = "ok" if stats.ok else "FAIL"
        extra = ""
        if stats.error:
            extra = f" error={stats.error!r}"
        if stats.quarantined:
            extra += " quarantined"
        print(
            f"  [{status}] {stats.vendor}/{stats.slug} "
            f"http={stats.http_status} listed={stats.listed} "
            f"upserted={stats.upserted} desc_w={stats.descriptions_written} "
            f"desc_skip={stats.descriptions_skipped} "
            f"deactivated={stats.deactivated}{extra}"
        )
    return 0 if result.boards_failed == 0 else 2


def cmd_normalize_locations(args: argparse.Namespace) -> int:
    with Session(engine) as session:
        n = backfill_locations(
            session,
            limit=args.limit,
            force=bool(getattr(args, "force", False)),
        )
    print(f"normalize-locations: updated={n}")
    return 0


def cmd_embed_postings(args: argparse.Namespace) -> int:
    with Session(engine) as session:
        n = backfill_embeddings(session, limit=args.limit)
    print(f"embed-postings: embedded={n}")
    return 0


def cmd_notify(args: argparse.Namespace) -> int:
    with Session(engine) as session:
        result = notify_all_users(session)
    print(
        f"notify: users={result.users} notified={result.notified} "
        f"(cap/floor from Settings; channel=in_app + optional webhook)"
    )
    return 0


def cmd_daily(args: argparse.Namespace) -> int:
    """File-locked daily: ingest → normalize → embed → notify. No user id on ingest."""
    result = run_daily(
        skip_notify=bool(args.skip_notify),
        skip_embed=bool(args.skip_embed),
    )
    if result.skipped_locked:
        print("daily: skipped (another run holds the lock)", file=sys.stderr)
        return 3
    ingest = result.ingest
    notify = result.notify
    print(
        f"daily complete in {result.elapsed_seconds:.1f}s: "
        f"locations={result.locations_updated} "
        f"embeddings={result.embeddings_written}"
    )
    if ingest is not None:
        print(
            "  ingest: "
            f"attempted={ingest.boards_attempted} ok={ingest.boards_ok} "
            f"failed={ingest.boards_failed} quarantined={ingest.boards_quarantined} "
            f"upserted={ingest.postings_upserted}"
        )
    if notify is not None:
        print(f"  notify: users={notify.users} notified={notify.notified}")
    elif args.skip_notify:
        print("  notify: skipped")
    return 0 if ingest is None or ingest.boards_failed == 0 else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="updateapply-catalog",
        description="Company board seed/directory + ATS ingest + daily run.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    seed = sub.add_parser(
        "seed-boards",
        help="Upsert bounded company_board seed from a JSON data file",
    )
    seed.add_argument(
        "--file",
        help=f"Seed JSON path (default: {DEFAULT_SEED_PATH})",
    )
    seed.set_defaults(func=cmd_seed_boards)

    directory = sub.add_parser(
        "import-directory",
        help="Upsert full ATS Company Directory (CC-BY-4.0); does not ingest",
    )
    directory.add_argument(
        "--file",
        help=f"CSV path (default: {DEFAULT_DIRECTORY_PATH})",
    )
    directory.add_argument(
        "--download",
        action="store_true",
        help="Download the public CSV before import (also downloads if file missing)",
    )
    directory.set_defaults(func=cmd_import_directory)

    ingest = sub.add_parser(
        "ingest",
        help="Ingest active boards into job_posting (no user id)",
    )
    ingest.add_argument(
        "--slug",
        help="Limit to one active board slug (debug)",
    )
    ingest.set_defaults(func=cmd_ingest)

    norm = sub.add_parser(
        "normalize-locations",
        help="Backfill location_remote / countries / parse_status on job_posting",
    )
    norm.add_argument("--limit", type=int, default=None, help="Max rows")
    norm.add_argument(
        "--force",
        action="store_true",
        help="Re-parse all rows (heal failed/partial after parser improvements)",
    )
    norm.set_defaults(func=cmd_normalize_locations)

    embed = sub.add_parser(
        "embed-postings",
        help="Embed active job_posting rows missing a vector (needs OPENROUTER_API_KEY)",
    )
    embed.add_argument("--limit", type=int, default=None, help="Max rows")
    embed.set_defaults(func=cmd_embed_postings)

    notify = sub.add_parser(
        "notify",
        help="Notify users about new strong matches (in-app log + optional webhook)",
    )
    notify.set_defaults(func=cmd_notify)

    daily = sub.add_parser(
        "daily",
        help="File-locked daily: ingest → normalize → embed → notify",
    )
    daily.add_argument(
        "--skip-notify",
        action="store_true",
        help="Run ingest/normalize/embed only",
    )
    daily.add_argument(
        "--skip-embed",
        action="store_true",
        help="Skip embedding backfill (faster dry runs)",
    )
    daily.set_defaults(func=cmd_daily)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
