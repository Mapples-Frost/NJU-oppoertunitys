from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from radar.classifiers.rule_classifier import classify
from radar.dedup import enrich_identity, merge_duplicates
from radar.extractors.deadline_extractor import extract_dates
from radar.fetchers import fetch_source
from radar.mailer.render_email import render_email
from radar.mailer.render_history import render_history_email
from radar.mailer.send_email import send_email
from radar.models import Opportunity, RunSummary
from radar.rankers.opportunity_ranker import rank
from radar.storage.db import Database
from radar.utils.config import enabled_sources, load_config
from radar.utils.logging import configure_logging

LOGGER = logging.getLogger(__name__)


def _process_item(item: Opportunity, keywords: dict, scoring: dict) -> Opportunity:
    dates = extract_dates(item.title, item.content)
    item.deadline_at = dates["deadline_at"]
    item.event_start_at = dates["event_start_at"]
    item.event_end_at = dates["event_end_at"]
    item.date_confidence = dates["date_confidence"]
    item.date_source_text = dates["date_source_text"]
    item = classify(item)
    item = rank(item, keywords, scoring)
    return enrich_identity(item)


def _apply_source_metadata(item: Opportunity, source: dict) -> Opportunity:
    item.source_pack = item.source_pack or source.get("source_pack", "")
    item.source_domain = item.source_domain or source.get("domain", "")
    item.source_tier = item.source_tier or source.get("source_tier", "")
    return item


def _init_pack_stats(sources: list[dict]) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    for source in sources:
        pack = source.get("source_pack", "unknown_pack")
        stats.setdefault(pack, {"total": 0, "successful": 0, "failed": 0, "items": 0, "new_items": 0})
        stats[pack]["total"] += 1
    return stats


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _send_history_email(args: argparse.Namespace, config: dict) -> int:
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    logs_dir = Path(args.logs)
    logs_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "id": datetime.now().astimezone().strftime("%Y%m%d%H%M%S"),
        "mode": "history_email",
        "started_at": started,
        "finished_at": None,
        "status": "running",
        "total_history_items": 0,
        "included_items": 0,
        "history_min_score": args.history_min_score,
        "history_limit": args.history_limit,
        "email_status": "not_requested",
        "email_skip_reason": "",
    }
    database = Database(Path(args.db))
    try:
        database.migrate()
        total_count = database.count_opportunities(args.history_min_score)
        limit = args.history_limit if args.history_limit and args.history_limit > 0 else None
        items = database.list_opportunities(args.history_min_score, limit=limit)
        summary["total_history_items"] = total_count
        summary["included_items"] = len(items)
        rendered = render_history_email(items, config["email"], total_count=total_count)
        (logs_dir / "latest_history_email.html").write_text(rendered["html"], encoding="utf-8")
        (logs_dir / "latest_history_email.txt").write_text(rendered["text"], encoding="utf-8")

        if args.dry_run:
            summary["email_status"] = "disabled"
            summary["email_skip_reason"] = "--dry-run was provided"
            return_code = 0
        else:
            summary["email_status"] = "sending"
            send_email(rendered["subject"], rendered["text"], rendered["html"])
            summary["email_status"] = "sent"
            LOGGER.info("history email sent with %s items", len(items))
            return_code = 0
        summary["status"] = "success"
    except Exception as exc:
        LOGGER.exception("history email failed")
        summary["status"] = "failed"
        summary["email_status"] = "failed"
        summary["email_skip_reason"] = str(exc)
        return_code = 1
    finally:
        summary["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        _write_json(logs_dir / "latest_history_run.json", summary)
        database.close()
    if args.dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return return_code


def run(args: argparse.Namespace) -> int:
    config_dir = Path(args.config).resolve()
    project_root = config_dir.parent
    config = load_config(config_dir)

    if args.send_history_email:
        return _send_history_email(args, config)

    sources = enabled_sources(config)
    if args.limit_sources:
        sources = sources[: args.limit_sources]

    started = datetime.now().astimezone().isoformat(timespec="seconds")
    run_summary = RunSummary(
        id=datetime.now().astimezone().strftime("%Y%m%d%H%M%S"),
        started_at=started,
        total_sources=len(sources),
        pack_stats=_init_pack_stats(sources),
    )
    all_items: list[Opportunity] = []
    failures: list[dict[str, str]] = []

    database: Database | None = None
    if not args.dry_run:
        database = Database(Path(args.db))
        database.migrate()
        database.insert_run(run_summary)

    try:
        for source in sources:
            LOGGER.info("fetching %s", source.get("id"))
            source_started_at = datetime.now().astimezone().isoformat(timespec="seconds")
            result = fetch_source(source, project_root)
            result.source_pack = result.source_pack or source.get("source_pack", "")
            result.source_domain = result.source_domain or source.get("domain", "")
            result.source_tier = result.source_tier or source.get("source_tier", "")
            result.items = [_apply_source_metadata(item, source) for item in result.items]
            all_items.extend(result.items)
            pack = source.get("source_pack", "unknown_pack")
            run_summary.pack_stats.setdefault(
                pack,
                {"total": 0, "successful": 0, "failed": 0, "items": 0, "new_items": 0},
            )
            run_summary.pack_stats[pack]["items"] += len(result.items)
            if result.ok:
                run_summary.successful_sources += 1
                run_summary.pack_stats[pack]["successful"] += 1
            else:
                run_summary.failed_sources += 1
                run_summary.pack_stats[pack]["failed"] += 1
                failures.append(
                    {
                        "source_id": result.source_id,
                        "source_name": result.source_name,
                        "source_pack": pack,
                        "domain": source.get("domain", ""),
                        "error": result.error or "unknown error",
                    }
                )
            if database:
                database.upsert_source(source, success=result.ok, error=result.error, total_found=len(result.items))
                database.insert_source_run(
                    run_summary.id,
                    source,
                    "success" if result.ok else "failed",
                    len(result.items),
                    result.error,
                    source_started_at,
                    datetime.now().astimezone().isoformat(timespec="seconds"),
                )

        run_summary.total_items = len(all_items)
        processed = [
            _process_item(item, config["keywords"], config["scoring"])
            for item in all_items
            if item.title and (item.url or item.content)
        ]
        deduped = merge_duplicates(processed)
        deduped.sort(key=lambda item: item.score, reverse=True)

        new_items: list[Opportunity] = []
        if database:
            for item in deduped:
                if database.upsert_opportunity(item):
                    new_items.append(item)
        else:
            new_items = deduped
        run_summary.new_items = len(new_items)
        for item in new_items:
            pack = item.source_pack or "unknown_pack"
            run_summary.pack_stats.setdefault(
                pack,
                {"total": 0, "successful": 0, "failed": 0, "items": 0, "new_items": 0},
            )
            run_summary.pack_stats[pack]["new_items"] += 1

        rendered = render_email(
            new_items,
            run_summary,
            failures,
            config["email"],
            config["scoring"],
        )
        logs_dir = Path(args.logs)
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "latest_email.html").write_text(rendered["html"], encoding="utf-8")
        (logs_dir / "latest_email.txt").write_text(rendered["text"], encoding="utf-8")

        if args.send_email:
            if rendered["eligible"] or config["email"].get("send_empty", False):
                run_summary.email_status = "sending"
                send_email(rendered["subject"], rendered["text"], rendered["html"])
                run_summary.email_status = "sent"
                run_summary.emailed_items = len(rendered["eligible"])
                LOGGER.info("email sent with %s eligible items", run_summary.emailed_items)
            else:
                run_summary.email_status = "skipped"
                run_summary.email_skip_reason = "no eligible items and send_empty is false"
                LOGGER.info("no eligible items; email skipped")
        else:
            run_summary.email_status = "disabled"
            run_summary.email_skip_reason = "--send-email was not provided"

        run_summary.status = "success"
        return_code = 0
    except Exception as exc:
        LOGGER.exception("radar run failed")
        run_summary.status = "failed"
        if run_summary.email_status == "sending":
            run_summary.email_status = "failed"
            run_summary.email_skip_reason = str(exc)
        failures.append({"source_id": "system", "source_name": "system", "error": str(exc)})
        return_code = 1
    finally:
        run_summary.finished_at = datetime.now().astimezone().isoformat(timespec="seconds")
        run_summary.errors = failures
        _write_json(Path(args.logs) / "latest_run.json", asdict(run_summary))
        if database:
            database.insert_run(run_summary)
            database.close()

    if args.dry_run:
        print(json.dumps(asdict(run_summary), ensure_ascii=False, indent=2))
    return return_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NJU Opportunity Radar")
    parser.add_argument("--config", default="config", help="config directory")
    parser.add_argument("--db", default="data/opportunities.sqlite", help="SQLite database path")
    parser.add_argument("--logs", default="logs", help="log output directory")
    parser.add_argument("--dry-run", action="store_true", help="fetch and render without writing the database")
    parser.add_argument("--send-email", action="store_true", help="send the rendered daily report through SMTP")
    parser.add_argument("--send-history-email", action="store_true", help="send all stored opportunities through SMTP")
    parser.add_argument("--history-limit", type=int, default=0, help="maximum history items to send; 0 means all")
    parser.add_argument("--history-min-score", type=float, default=0.0, help="minimum score for history email")
    parser.add_argument("--limit-sources", type=int, default=None, help="limit source count for local debugging")
    parser.add_argument("--verbose", action="store_true", help="enable debug logging")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
