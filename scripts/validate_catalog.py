#!/usr/bin/env python3
"""Validate the official-source catalog for completeness and duplicates."""
from __future__ import annotations

import csv
import hashlib
import pathlib
import sys
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOG = ROOT / "sources" / "catalog.csv"
REQUIRED = {
    "id",
    "level",
    "topic",
    "title",
    "issuer",
    "status",
    "evidence_grade",
    "official_page_url",
    "accessed_at",
}
OFFICIAL_SUFFIXES = (
    ".gov.cn",
    "gov.cn",
    ".qingdao.gov.cn",
    "qingdao.gov.cn",
)


def is_official(url: str) -> bool:
    if not url:
        return False
    host = (urlparse(url).hostname or "").lower()
    return any(host == suffix.lstrip(".") or host.endswith(suffix) for suffix in OFFICIAL_SUFFIXES)


def main() -> int:
    errors: list[str] = []
    with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing_fields = REQUIRED - fields
        if missing_fields:
            errors.append(f"catalog missing columns: {sorted(missing_fields)}")
        rows = list(reader)

    seen_ids: set[str] = set()
    seen_keys: set[tuple[str, str]] = set()
    for line_no, row in enumerate(rows, start=2):
        if None in row:
            errors.append(f"line {line_no}: extra CSV columns {row[None]}")

        for field in sorted(REQUIRED):
            if not (row.get(field) or "").strip():
                errors.append(f"line {line_no}: empty required field {field}")

        rid = row.get("id", "").strip()
        if rid in seen_ids:
            errors.append(f"line {line_no}: duplicate id {rid}")
        seen_ids.add(rid)

        key = (row.get("title", "").strip(), row.get("document_number", "").strip())
        if key in seen_keys and any(key):
            errors.append(f"line {line_no}: possible duplicate title/document number {key}")
        seen_keys.add(key)

        page_url = row.get("official_page_url", "").strip()
        file_url = row.get("official_file_url", "").strip()
        if page_url and not is_official(page_url):
            errors.append(f"line {line_no}: non-official page URL {page_url}")
        if file_url and not is_official(file_url):
            errors.append(f"line {line_no}: non-official file URL {file_url}")

        local = row.get("local_path", "").strip()
        expected = row.get("sha256", "").strip().lower()
        if local:
            path = ROOT / local
            if not path.is_file():
                errors.append(f"line {line_no}: missing local file {local}")
            elif expected:
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                if actual != expected:
                    errors.append(f"line {line_no}: sha256 mismatch {local}")
        elif expected:
            errors.append(f"line {line_no}: sha256 present without local_path")

        if row.get("evidence_grade", "").strip() not in {"A", "B", "C", "待核验"}:
            errors.append(f"line {line_no}: invalid evidence grade")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"OK: {len(rows)} catalog rows validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
