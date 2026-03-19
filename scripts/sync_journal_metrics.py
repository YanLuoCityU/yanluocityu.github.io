#!/usr/bin/env python3
"""Sync journal metrics from EasyScholar into Jekyll data files.

This script reads journal venues from Jekyll publication markdown files, queries
EasyScholar's public journal-rank endpoint, and writes a compact YAML file that
can be rendered on the publications page.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_API_BASE_URL = "https://www.easyscholar.cc/open/getPublicationRank"
DEFAULT_TIMEOUT = 30
SKIP_VENUE_PATTERNS = (
    r"\bpreprint\b",
    r"\bconference\b",
    r"\bmeeting\b",
    r"\bsymposium\b",
    r"\bworkshop\b",
    r"\bcongress\b",
    r"\bforum\b",
)


class JournalMetricsSyncError(RuntimeError):
    """Raised when the journal-metrics sync cannot proceed."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync journal impact factor and JCR quartile from EasyScholar."
    )
    parser.add_argument(
        "--publications-dir",
        default="_publications",
        help="Directory containing Jekyll publication markdown files.",
    )
    parser.add_argument(
        "--output",
        default="_data/journal_metrics.yml",
        help="YAML file to write journal metrics into.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("EASYSCHOLAR_API_KEY"),
        help="EasyScholar API key. Defaults to EASYSCHOLAR_API_KEY.",
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("EASYSCHOLAR_API_BASE_URL", DEFAULT_API_BASE_URL),
        help="EasyScholar journal-rank endpoint.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Network timeout in seconds.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the YAML output without writing the file.",
    )
    return parser.parse_args()


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_value = re.sub(r"[^a-zA-Z0-9]+", " ", ascii_value).lower()
    return re.sub(r"\s+", " ", ascii_value).strip()


def yaml_quote(value: str) -> str:
    clean = re.sub(r"\s+", " ", value).strip()
    return "'" + clean.replace("'", "''") + "'"


def should_skip_venue(venue: str) -> bool:
    normalized = normalize_name(venue)
    if not normalized:
        return True
    return any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in SKIP_VENUE_PATTERNS)


def extract_front_matter_value(content: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", content, flags=re.MULTILINE)
    if not match:
        return None

    raw_value = match.group(1).strip()
    if raw_value.startswith("'") and raw_value.endswith("'"):
        return raw_value[1:-1].replace("''", "'")
    if raw_value.startswith('"') and raw_value.endswith('"'):
        return raw_value[1:-1]
    return raw_value


def discover_venues(publications_dir: Path) -> list[str]:
    if not publications_dir.exists():
        raise JournalMetricsSyncError(f"Publications directory not found: {publications_dir}")

    venues: set[str] = set()
    for path in publications_dir.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        venue = extract_front_matter_value(content, "venue")
        if not venue or should_skip_venue(venue):
            continue
        venues.add(venue)

    if not venues:
        raise JournalMetricsSyncError("No eligible journal venues found in _publications.")
    return sorted(venues, key=lambda value: normalize_name(value))


def build_request_url(api_base_url: str, api_key: str, venue: str) -> str:
    query = urlencode({"secretKey": api_key, "publicationName": venue})
    return f"{api_base_url}?{query}"


def read_json(url: str, timeout: int) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "yanluo-easyscholar-sync/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise JournalMetricsSyncError(f"EasyScholar request failed ({exc.code}) for {url}: {details}") from exc
    except URLError as exc:
        raise JournalMetricsSyncError(f"Could not reach EasyScholar endpoint {url}: {exc}") from exc


def extract_metric_value(node: Any, key: str) -> str | None:
    if not isinstance(node, dict):
        return None
    value = node.get(key)
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"-", "--", "\u6682\u65e0", "None", "null"}:
        return None
    return text


def fetch_metrics(api_base_url: str, api_key: str, venue: str, timeout: int) -> dict[str, str] | None:
    url = build_request_url(api_base_url, api_key, venue)
    payload = read_json(url, timeout)

    code = payload.get("code")
    if code not in {200, "200"}:
        message = payload.get("msg") or payload.get("message") or f"Unexpected response code: {code}"
        raise JournalMetricsSyncError(f"EasyScholar returned an error for '{venue}': {message}")

    data = payload.get("data") or {}
    official_rank = data.get("officialRank") or {}
    select_rank = official_rank.get("select") if isinstance(official_rank, dict) else {}
    all_rank = official_rank.get("all") if isinstance(official_rank, dict) else {}

    impact_factor = extract_metric_value(select_rank, "sciif") or extract_metric_value(all_rank, "sciif")
    jcr_quartile = extract_metric_value(select_rank, "sci") or extract_metric_value(all_rank, "sci")

    if not impact_factor and not jcr_quartile:
        return None

    metrics: dict[str, str] = {}
    if impact_factor:
        metrics["impact_factor"] = impact_factor
    if jcr_quartile:
        metrics["jcr_quartile"] = jcr_quartile
    return metrics

def build_yaml(metrics_by_venue: dict[str, dict[str, str]]) -> str:
    lines: list[str] = []
    for venue in sorted(metrics_by_venue, key=lambda value: normalize_name(value)):
        metrics = metrics_by_venue[venue]
        lines.append(f"{yaml_quote(venue)}:")
        if "impact_factor" in metrics:
            lines.append(f"  impact_factor: {yaml_quote(metrics['impact_factor'])}")
        if "jcr_quartile" in metrics:
            lines.append(f"  jcr_quartile: {yaml_quote(metrics['jcr_quartile'])}")
    return "\n".join(lines).rstrip() + "\n"


def write_text(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(content)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def sync_metrics(args: argparse.Namespace) -> int:
    if not args.api_key:
        raise JournalMetricsSyncError(
            "Missing EasyScholar API key. Set EASYSCHOLAR_API_KEY or pass --api-key."
        )

    repo_root = Path.cwd()
    publications_dir = (repo_root / args.publications_dir).resolve()
    output_path = (repo_root / args.output).resolve()

    venues = discover_venues(publications_dir)
    metrics_by_venue: dict[str, dict[str, str]] = {}
    skipped: list[str] = []

    for venue in venues:
        try:
            metrics = fetch_metrics(args.api_base_url, args.api_key, venue, args.timeout)
        except JournalMetricsSyncError as exc:
            print(f"WARNING: {exc}", file=sys.stderr)
            skipped.append(venue)
            continue

        if metrics:
            metrics_by_venue[venue] = metrics
        else:
            skipped.append(venue)
        time.sleep(0.5)

    yaml_output = build_yaml(metrics_by_venue)
    write_text(output_path, yaml_output, args.dry_run)

    print(f"Synced metrics for {len(metrics_by_venue)} journals into {output_path}.")
    if skipped:
        print(f"Skipped {len(skipped)} venues with no EasyScholar metrics.")
    return 0


def main() -> int:
    args = parse_args()
    try:
        return sync_metrics(args)
    except JournalMetricsSyncError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
