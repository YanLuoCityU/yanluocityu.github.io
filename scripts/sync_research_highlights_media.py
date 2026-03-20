#!/usr/bin/env python3
"""Fetch base media-coverage data from Nature metrics pages.\n\nThe generated JSON is the automatic source of truth for article metadata and raw mention lists.\nThe site then applies curated corrections from _data/research_highlights_media_manual.yml\nfor summary text and any mention lists that need manual cleanup or language-specific curation.\n"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_TIMEOUT = 30
DEFAULT_OUTPUT = '_data/research_highlights_media.json'
MOJIBAKE_MARKERS = ('\u00c3', '\u00e2', '\u00d0', '\u00d1', '\u00e3', '\ufffd')
HIGHLIGHTS = [
    {
        'slug': 'multiomics-cvd',
        'title': 'AI-based multiomics profiling reveals complementary omics contributions to personalized prediction of cardiovascular disease',
        'paper_url': 'https://doi.org/10.1038/s41467-026-68956-6',
        'metrics_url': 'https://www.nature.com/articles/s41467-026-68956-6/metrics',
        'journal': 'Nature Communications',
    },
    {
        'slug': 'internet-mental-health',
        'title': 'Positive association between Internet use and mental health among adults aged 50 years in 23 countries',
        'paper_url': 'https://doi.org/10.1038/s41562-024-02048-7',
        'metrics_url': 'https://www.nature.com/articles/s41562-024-02048-7/metrics',
        'journal': 'Nature Human Behaviour',
    },
]


class MediaSyncError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Sync research-highlight media mentions from Nature metrics pages.')
    parser.add_argument('--output', default=DEFAULT_OUTPUT, help='JSON file to write under _data/.')
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT, help='Network timeout in seconds.')
    parser.add_argument('--dry-run', action='store_true', help='Print JSON output without writing the file.')
    return parser.parse_args()


def read_text(url: str, timeout: int) -> str:
    request = Request(url, headers={'User-Agent': 'yanluo-media-sync/1.0'})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode('utf-8', errors='replace')
    except HTTPError as exc:
        details = exc.read().decode('utf-8', errors='ignore')
        raise MediaSyncError(f'Nature request failed ({exc.code}) for {url}: {details}') from exc
    except URLError as exc:
        raise MediaSyncError(f'Could not reach Nature metrics page {url}: {exc}') from exc


def looks_mojibake(value: str) -> bool:
    return any(marker in value for marker in MOJIBAKE_MARKERS)


def maybe_fix_mojibake(value: str) -> str:
    repaired = value
    for _ in range(3):
        if not looks_mojibake(repaired):
            break
        changed = False
        for source_encoding in ('latin-1', 'cp1252'):
            try:
                candidate = repaired.encode(source_encoding).decode('utf-8')
            except UnicodeError:
                continue
            if candidate != repaired:
                repaired = candidate
                changed = True
                break
        if not changed:
            break
    return repaired


def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r'<.*?>', '', value, flags=re.S)
    value = re.sub(r'\s+', ' ', value).strip()
    return maybe_fix_mojibake(value)


def parse_metrics_page(page_html: str, fallback: dict[str, str]) -> dict[str, object]:
    title_match = re.search(r'<h1 class="c-article-metrics__heading[^>]*>\s*<a[^>]*>(.*?)</a>', page_html, flags=re.S)
    parsed_title = clean_text(title_match.group(1)) if title_match else ''
    title = fallback['title'] if not parsed_title or looks_mojibake(parsed_title) else parsed_title

    score_match = re.search(r'Altmetric score\s*(\d+)', page_html, flags=re.I)
    news_count_match = re.search(r'<span>(\d+)\s+news outlets</span>', page_html, flags=re.I)

    section_match = re.search(
        r'<div class="c-article-metrics__section" data-test="metrics-mentions">.*?<ul class="c-article-metrics__posts u-list-reset">(.*?)</ul>',
        page_html,
        flags=re.S,
    )
    mentions_html = section_match.group(1) if section_match else ''
    item_matches = re.findall(
        r'<li>\s*<div class="c-card">\s*<h3 class="c-card__title">\s*<a href="([^"]*)"[^>]*>(.*?)</a>\s*</h3>\s*<span>(.*?)</span>',
        mentions_html,
        flags=re.S,
    )

    mentions: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for url, raw_title, raw_source in item_matches:
        title_text = clean_text(raw_title)
        source_text = clean_text(raw_source)
        cleaned_url = html.unescape(url).strip()
        if not title_text or not source_text:
            continue
        key = (title_text, source_text, cleaned_url)
        if key in seen:
            continue
        seen.add(key)
        mentions.append(
            {
                'title': title_text,
                'source': source_text,
                'url': cleaned_url,
            }
        )

    return {
        'slug': fallback['slug'],
        'title': title,
        'journal': fallback['journal'],
        'paper_url': fallback['paper_url'],
        'metrics_url': fallback['metrics_url'],
        'altmetric_score': int(score_match.group(1)) if score_match else None,
        'news_outlets': int(news_count_match.group(1)) if news_count_match else None,
        'mentions': mentions,
    }


def write_output(path: Path, payload: dict[str, object], dry_run: bool) -> None:
    content = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
    if dry_run:
        print(content)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def main() -> int:
    args = parse_args()
    try:
        highlights = []
        for item in HIGHLIGHTS:
            page_html = read_text(item['metrics_url'], args.timeout)
            highlights.append(parse_metrics_page(page_html, item))
        payload = {'highlights': highlights}
        write_output((Path.cwd() / args.output).resolve(), payload, args.dry_run)
        print(f'Synced media coverage for {len(highlights)} research highlights into {args.output}.')
        return 0
    except MediaSyncError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
