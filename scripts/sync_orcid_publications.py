#!/usr/bin/env python3
"""Sync ORCID public works into Jekyll publication markdown files."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_API_BASE_URL = "https://pub.orcid.org/v3.0"
DEFAULT_TOKEN_URL = "https://orcid.org/oauth/token"
DEFAULT_TIMEOUT = 30
DEFAULT_DATE = "1900-01-01"
SOURCE_TAG = "orcid"
EXCLUDED_ORCID_WORK_TYPES = {
    "conference abstract",
    "conference paper",
    "conference poster",
    "conference presentation",
}


@dataclass
class PublicationRecord:
    put_code: str
    title: str
    slug: str
    date: str
    category: str
    venue: str
    work_type: str
    authors: list[str]
    excerpt: str | None
    citation: str | None
    bibtex: str | None
    paper_url: str | None


class OrcidSyncError(RuntimeError):
    """Raised when the ORCID sync cannot proceed."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync ORCID works into Jekyll _publications markdown files."
    )
    parser.add_argument("--orcid", help="ORCID iD or full ORCID URL. Defaults to _config.yml author.orcid.")
    parser.add_argument("--config", default="_config.yml", help="Path to the Jekyll config file.")
    parser.add_argument("--output-dir", default="_publications", help="Directory for generated publication markdown files.")
    parser.add_argument("--files-dir", default="files", help="Directory for generated BibTeX assets.")
    parser.add_argument("--api-base-url", default=os.getenv("ORCID_API_BASE_URL", DEFAULT_API_BASE_URL), help="Base URL for the ORCID API.")
    parser.add_argument("--token-url", default=os.getenv("ORCID_TOKEN_URL", DEFAULT_TOKEN_URL), help="OAuth token URL for ORCID.")
    parser.add_argument("--access-token", default=os.getenv("ORCID_ACCESS_TOKEN"), help="Existing ORCID /read-public access token.")
    parser.add_argument("--client-id", default=os.getenv("ORCID_CLIENT_ID"), help="ORCID Public API client ID.")
    parser.add_argument("--client-secret", default=os.getenv("ORCID_CLIENT_SECRET"), help="ORCID Public API client secret.")
    parser.add_argument("--allow-anonymous", action="store_true", help="Allow unauthenticated reads for manual, low-volume use when no token or client credentials are configured.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned file changes without writing them.")
    parser.add_argument("--keep-stale", action="store_true", help="Keep stale ORCID-generated files instead of deleting them.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Network timeout in seconds.")
    return parser.parse_args()


def extract_orcid_id(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", value, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def extract_config_value(raw_line: str) -> str:
    return raw_line.split(":", 1)[1].split("#", 1)[0].strip().strip('"\'')


def read_orcid_from_config(config_path: Path) -> str | None:
    if not config_path.exists():
        return None

    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not re.match(r"^orcid\s*:", line):
            continue
        return extract_orcid_id(extract_config_value(raw_line))
    return None


def read_author_name_from_config(config_path: Path) -> str | None:
    if not config_path.exists():
        return None

    in_author_block = False
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped == "author:":
            in_author_block = True
            continue

        if in_author_block:
            if raw_line == raw_line.lstrip():
                in_author_block = False
            elif re.match(r"^\s+name\s*:", raw_line):
                return extract_config_value(raw_line)

    return None


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug or "publication"


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


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    clean = html.unescape(value)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean or None


def nested_value(node: Any, *keys: str) -> Any:
    current: Any = node
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def normalize_date(publication_date: dict[str, Any] | None) -> str:
    if not publication_date:
        return DEFAULT_DATE

    year = nested_value(publication_date, "year", "value")
    month = nested_value(publication_date, "month", "value") or "01"
    day = nested_value(publication_date, "day", "value") or "01"

    if not year:
        return DEFAULT_DATE

    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def extract_identifiers(work: dict[str, Any]) -> list[tuple[str, str, str | None]]:
    identifiers: list[tuple[str, str, str | None]] = []
    external_ids = work.get("external-ids", {}).get("external-id", [])
    for item in external_ids:
        id_type = normalize_text(item.get("external-id-type"))
        id_value = normalize_text(item.get("external-id-value"))
        id_url = normalize_text(nested_value(item, "external-id-url", "value"))
        if id_type and id_value:
            identifiers.append((id_type, id_value, id_url))
    return identifiers


def choose_paper_url(work: dict[str, Any], identifiers: list[tuple[str, str, str | None]]) -> str | None:
    direct_url = normalize_text(nested_value(work, "url", "value"))

    for id_type, id_value, id_url in identifiers:
        if id_type.lower() == "doi":
            return id_url or f"https://doi.org/{id_value}"

    return direct_url or next((id_url for _, _, id_url in identifiers if id_url), None)


def extract_citation(work: dict[str, Any]) -> tuple[str | None, str | None]:
    citation = work.get("citation")
    if not citation:
        return None, None

    citation_type = normalize_text(citation.get("citation-type"))
    citation_value = normalize_text(citation.get("citation-value"))
    if not citation_value:
        return None, None

    if citation_type and citation_type.lower() == "bibtex":
        return None, citation_value
    return citation_value, None


def fallback_citation(title: str, venue: str, date: str) -> str:
    year = date[:4]
    if venue:
        return f"{title}. {venue}. {year}."
    return f"{title}. {year}."


def fallback_venue(work_type: str | None) -> str:
    if not work_type:
        return "ORCID work"
    return work_type.replace("-", " ").title()


def should_highlight_author(name: str, author_name: str | None) -> bool:
    normalized = normalize_name(name)
    if not normalized:
        return False

    tokens = normalized.split()
    if "luo" not in tokens:
        return False

    if "yan" in tokens or "y" in tokens:
        return True

    if author_name:
        author_tokens = normalize_name(author_name).split()
        if "luo" in author_tokens and ("yan" in author_tokens or "y" in author_tokens):
            if "luo" in tokens and any(token in tokens for token in ("yan", "y")):
                return True

    return False


def format_authors(contributors: list[str], author_name: str | None) -> list[str]:
    formatted: list[str] = []
    for contributor in contributors:
        display = contributor
        if should_highlight_author(contributor, author_name):
            display = f"<strong>{contributor}</strong>"
        formatted.append(display)
    return formatted


def extract_contributor_names(work: dict[str, Any]) -> list[str]:
    contributors = work.get("contributors", {}).get("contributor", [])
    names: list[str] = []
    for contributor in contributors:
        name = normalize_text(nested_value(contributor, "credit-name", "value"))
        if name:
            names.append(name)
    return names


def extract_authors_from_bibtex(bibtex: str | None) -> list[str]:
    if not bibtex:
        return []

    match = re.search(r"author\s*=\s*\{([^}]*)\}", bibtex, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return []

    raw_authors = match.group(1)
    authors = []
    for item in re.split(r"\s+and\s+", raw_authors):
        author = normalize_text(item)
        if author:
            authors.append(author)
    return authors


def is_preprint(work_type: str, venue: str) -> bool:
    normalized_type = normalize_name(work_type)
    normalized_venue = normalize_name(venue)
    return normalized_type in {"preprint", "working paper", "dissertation thesis"} or "preprint" in normalized_venue


def should_sync_work(work: dict[str, Any]) -> bool:
    work_type = normalize_name(normalize_text(work.get("type")) or "")
    return work_type not in EXCLUDED_ORCID_WORK_TYPES


def build_publication_record(work: dict[str, Any], author_name: str | None) -> PublicationRecord:
    put_code = str(work.get("put-code") or "")
    title_value = normalize_text(nested_value(work, "title", "title", "value")) or f"ORCID work {put_code}"
    subtitle_value = normalize_text(nested_value(work, "title", "subtitle", "value"))
    title = f"{title_value}: {subtitle_value}" if subtitle_value else title_value

    work_type = normalize_text(work.get("type")) or "journal-article"
    venue = normalize_text(nested_value(work, "journal-title", "value")) or fallback_venue(work_type)
    date = normalize_date(work.get("publication-date"))
    excerpt = normalize_text(work.get("short-description"))
    identifiers = extract_identifiers(work)
    paper_url = choose_paper_url(work, identifiers)
    citation, bibtex = extract_citation(work)
    if not citation:
        citation = fallback_citation(title, venue, date)

    contributor_names = extract_contributor_names(work)
    if not contributor_names:
        contributor_names = extract_authors_from_bibtex(bibtex)
    formatted_authors = format_authors(contributor_names, author_name)
    category = "preprint" if is_preprint(work_type, venue) else "publication"
    slug = f"{slugify(title)}-{put_code}" if put_code else slugify(title)

    return PublicationRecord(
        put_code=put_code,
        title=title,
        slug=slug,
        date=date,
        category=category,
        venue=venue,
        work_type=work_type,
        authors=formatted_authors,
        excerpt=excerpt,
        citation=citation,
        bibtex=bibtex,
        paper_url=paper_url,
    )


def build_markdown(record: PublicationRecord, orcid_id: str, bibtex_url: str | None) -> str:
    front_matter = [
        "---",
        f"title: {yaml_quote(record.title)}",
        "collection: publications",
        f"category: {record.category}",
        f"permalink: /publication/{record.date}-{record.slug}",
        f"date: {record.date}",
        f"venue: {yaml_quote(record.venue)}",
    ]

    if record.authors:
        front_matter.append(f"authors: {yaml_quote(', '.join(record.authors))}")
    if record.excerpt:
        front_matter.append(f"excerpt: {yaml_quote(record.excerpt)}")
    if record.paper_url:
        front_matter.append(f"paperurl: {yaml_quote(record.paper_url)}")
    if record.citation:
        front_matter.append(f"citation: {yaml_quote(record.citation)}")
    if bibtex_url:
        front_matter.append(f"bibtexurl: {yaml_quote(bibtex_url)}")

    front_matter.extend(
        [
            f"source: {SOURCE_TAG}",
            f"orcid_id: {yaml_quote(orcid_id)}",
            f"orcid_put_code: {record.put_code}",
            f"orcid_work_type: {yaml_quote(record.work_type)}",
            "---",
            "",
        ]
    )

    return "\n".join(front_matter).rstrip() + "\n"


def build_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/orcid+json",
        "User-Agent": "yanluo-orcid-sync/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def read_json(url: str, token: str | None, timeout: int) -> dict[str, Any]:
    request = Request(url, headers=build_headers(token))
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise OrcidSyncError(f"ORCID request failed ({exc.code}) for {url}: {details}") from exc
    except URLError as exc:
        raise OrcidSyncError(f"Could not reach ORCID endpoint {url}: {exc}") from exc


def fetch_access_token(client_id: str, client_secret: str, token_url: str, timeout: int) -> str:
    payload = urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "/read-public",
        }
    ).encode("utf-8")
    request = Request(
        token_url,
        data=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "yanluo-orcid-sync/1.0",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise OrcidSyncError(f"Could not obtain ORCID access token ({exc.code}): {details}") from exc
    except URLError as exc:
        raise OrcidSyncError(f"Could not reach ORCID token endpoint {token_url}: {exc}") from exc

    token = data.get("access_token")
    if not token:
        raise OrcidSyncError("ORCID token response did not contain access_token.")
    return token


def resolve_access_token(args: argparse.Namespace) -> str | None:
    if args.access_token:
        return args.access_token
    if args.client_id and args.client_secret:
        return fetch_access_token(args.client_id, args.client_secret, args.token_url, args.timeout)
    if args.allow_anonymous:
        return None

    raise OrcidSyncError(
        "Missing ORCID credentials. Set ORCID_ACCESS_TOKEN or ORCID_CLIENT_ID / ORCID_CLIENT_SECRET, "
        "or rerun with --allow-anonymous for low-volume manual use."
    )


def fetch_work_put_codes(orcid_id: str, api_base_url: str, token: str | None, timeout: int) -> list[str]:
    works_url = f"{api_base_url.rstrip('/')}/{orcid_id}/works"
    payload = read_json(works_url, token, timeout)

    put_codes: list[str] = []
    for group in payload.get("group", []):
        summaries = group.get("work-summary", [])
        if not summaries:
            continue
        summaries = sorted(
            summaries,
            key=lambda item: int(item.get("display-index") or 0),
            reverse=True,
        )
        put_code = summaries[0].get("put-code")
        if put_code is not None:
            put_codes.append(str(put_code))
    return put_codes


def fetch_work_records(orcid_id: str, api_base_url: str, token: str | None, timeout: int, author_name: str | None) -> list[PublicationRecord]:
    records: list[PublicationRecord] = []
    for put_code in fetch_work_put_codes(orcid_id, api_base_url, token, timeout):
        work_url = f"{api_base_url.rstrip('/')}/{orcid_id}/work/{put_code}"
        work_payload = read_json(work_url, token, timeout)
        if not should_sync_work(work_payload):
            continue
        records.append(build_publication_record(work_payload, author_name))
    return sorted(records, key=lambda item: (item.date, item.title.lower()))


def discover_generated_markdown(output_dir: Path) -> set[Path]:
    generated: set[Path] = set()
    if not output_dir.exists():
        return generated
    for path in output_dir.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        if re.search(r"^source:\s*orcid\s*$", content, flags=re.MULTILINE):
            generated.add(path)
    return generated


def ensure_directory(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] write {path}")
        return
    path.write_text(content, encoding="utf-8")


def delete_path(path: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] delete {path}")
        return
    if path.exists():
        path.unlink()


def sync_publications(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()
    config_path = (repo_root / args.config).resolve()
    output_dir = (repo_root / args.output_dir).resolve()
    bib_dir = (repo_root / args.files_dir / "orcid-bib").resolve()

    orcid_id = extract_orcid_id(args.orcid) or read_orcid_from_config(config_path)
    if not orcid_id:
        raise OrcidSyncError("Could not determine ORCID iD. Pass --orcid or set author.orcid in _config.yml.")

    author_name = read_author_name_from_config(config_path)
    token = resolve_access_token(args)
    if token:
        print("Using authenticated ORCID /read-public access.")
    else:
        print("Using anonymous ORCID access for low-volume manual sync.")

    publications = fetch_work_records(orcid_id, args.api_base_url, token, args.timeout, author_name)
    if not publications:
        print(f"No ORCID works found for {orcid_id}.")
        return 0

    ensure_directory(output_dir, args.dry_run)
    ensure_directory(bib_dir, args.dry_run)

    expected_markdown_paths: set[Path] = set()
    expected_bib_paths: set[Path] = set()

    for record in publications:
        basename = f"{record.date}-{record.slug}"
        markdown_path = output_dir / f"{basename}.md"
        bib_path = bib_dir / f"{basename}.bib"
        bibtex_url = f"/files/orcid-bib/{basename}.bib" if record.bibtex else None
        markdown = build_markdown(record, orcid_id, bibtex_url)

        write_text(markdown_path, markdown, args.dry_run)
        expected_markdown_paths.add(markdown_path)

        if record.bibtex:
            write_text(bib_path, record.bibtex.rstrip() + "\n", args.dry_run)
            expected_bib_paths.add(bib_path)

    if not args.keep_stale:
        stale_markdown = discover_generated_markdown(output_dir) - expected_markdown_paths
        for path in sorted(stale_markdown):
            delete_path(path, args.dry_run)

        if bib_dir.exists():
            stale_bib = set(bib_dir.glob("*.bib")) - expected_bib_paths
            for path in sorted(stale_bib):
                delete_path(path, args.dry_run)

    print(f"Synced {len(publications)} ORCID works into {output_dir}.")
    return 0


def main() -> int:
    args = parse_args()
    try:
        return sync_publications(args)
    except OrcidSyncError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

