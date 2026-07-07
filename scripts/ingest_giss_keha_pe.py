#!/usr/bin/env python3
"""
Ingest ግስ ከሀ-ፐ (Ermias Gashu) grammar reference from Scribd text extraction.

Source: https://www.scribd.com/document/747503683
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "sources" / "giss_keha_pe_raw.json"
OUT_PATH = ROOT / "data" / "grammar_giss_keha_pe.json"

PATTERN_CODES = {
    "ቀተ": {"name": "perfective", "geez_name": "ቀዳማይ አንቀጽ", "english_name": "Perfective"},
    "ቀደ": {"name": "perfective_alt", "geez_name": "ቀዳማይ አንቀጽ", "english_name": "Perfective"},
    "ጦመ": {"name": "participle", "geez_name": "ሥራሴ", "english_name": "Participle"},
    "ተን": {"name": "noun_agent", "geez_name": "ስም ፈጣሪ", "english_name": "Agent Noun"},
    "ባረ": {"name": "adjective", "geez_name": "ስም መገለጫ", "english_name": "Adjective"},
    "ማህ": {"name": "adverb", "geez_name": "ግስ መገለጫ", "english_name": "Adverb"},
    "ሴሰ": {"name": "noun", "geez_name": "ስም", "english_name": "Noun"},
    "ርዕስ": {"name": "topic", "geez_name": "ርዕስ", "english_name": "Topic/Heading"},
    "ክህ": {"name": "conjugation_grid", "geez_name": "ክፍል", "english_name": "Conjugation grid marker"},
}

PATTERN_TOKEN = r"(?:ቀተ|ቀደ|ጦመ|ተን|ባረ|ማህ|ሴሰ|ርዕስ|ክህ)"
ENTRY_RE = re.compile(
    rf"(?P<meaning>[^❖/\-]+?)\s*(?P<pattern>{PATTERN_TOKEN}(?:\s*/\s*{PATTERN_TOKEN})*)"
    r"\s*(?:----|-----|---|-)\s*",
    re.UNICODE,
)
INLINE_ENTRY_RE = re.compile(
    rf"(?P<meaning>[^❖/]+?)(?P<pattern>{PATTERN_TOKEN}(?:/{PATTERN_TOKEN})*)"
    r"(?:----|-----|---|-)",
    re.UNICODE,
)

ROOT_MARKER_RE = re.compile(r"❖\s*(?P<root>[ሀ-ፐ]+)")
SECTION_RE = re.compile(r"^\d+$")


def is_summary_line(line: str) -> bool:
    return "----" in line and len(line) > 35 and "❖" not in line[:3]


def parse_summary_line(line: str) -> list[dict]:
    entries = []
    for match in ENTRY_RE.finditer(line + " "):
        entries.append(_entry_from_match(match))
    if not entries:
        for match in INLINE_ENTRY_RE.finditer(line):
            entries.append(_entry_from_match(match))
    return entries


def _entry_from_match(match: re.Match) -> dict:
    meaning = match.group("meaning").strip(" -")
    pattern_raw = match.group("pattern")
    patterns = [p.strip() for p in re.split(r"\s*/\s*", pattern_raw) if p.strip()]
    return {
        "meaning": meaning,
        "patterns": patterns,
        "pattern_info": [PATTERN_CODES.get(p, {"name": p}) for p in patterns],
    }


def ingest_page_texts(page_texts: list[dict]) -> list[str]:
    return [p.get("text", "") for p in page_texts if p.get("text")]


def ingest_lines(lines: list[str]) -> dict:
    sections: list[dict] = []
    current_section = {"id": 0, "title": "intro", "roots": [], "entries": []}
    current_root = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if SECTION_RE.match(line):
            if current_section["roots"] or current_section["entries"]:
                sections.append(current_section)
            current_section = {"id": int(line), "title": f"section_{line}", "roots": [], "entries": []}
            current_root = None
            continue

        root_match = ROOT_MARKER_RE.search(line)
        if root_match:
            current_root = root_match.group("root")
            current_section["roots"].append(current_root)
            # Page text may continue after ❖ root marker
            line = line[root_match.end() :].strip()
            if not line:
                continue

        if is_summary_line(line) or ("----" in line and any(code in line for code in PATTERN_CODES)):
            parsed = parse_summary_line(line)
            for item in parsed:
                item["section"] = current_section["id"]
                if current_root:
                    item["root_hint"] = current_root
                current_section["entries"].append(item)

    if current_section["roots"] or current_section["entries"]:
        sections.append(current_section)

    all_entries = [entry for section in sections for entry in section["entries"]]
    return {
        "source": {
            "title": "ግስ ከሀ-ፐ",
            "author": "Ermias Gashu",
            "url": "https://www.scribd.com/document/747503683",
            "pages": 34,
        },
        "pattern_codes": PATTERN_CODES,
        "sections": sections,
        "entry_count": len(all_entries),
        "entries": all_entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest ግስ ከሀ-ፐ grammar text")
    parser.add_argument(
        "--input",
        type=Path,
        default=RAW_PATH,
        help="Raw Scribd extraction JSON (with lines array)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUT_PATH,
        help="Structured grammar output path",
    )
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    lines = payload.get("lines", [])
    if not lines and payload.get("pageTexts"):
        lines = ingest_page_texts(payload["pageTexts"])
    result = ingest_lines(lines)
    result["source"]["extracted_pages"] = payload.get("totalPages") or len(payload.get("pageTexts", []))
    result["source"]["unique_lines"] = payload.get("uniqueLines")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.output} ({result['entry_count']} entries, {len(result['sections'])} sections)")

    index_script = Path(__file__).resolve().parent / "build_grammar_index.py"
    if index_script.exists():
        import subprocess
        subprocess.run([sys.executable, str(index_script)], check=False)


if __name__ == "__main__":
    main()
