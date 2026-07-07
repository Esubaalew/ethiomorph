#!/usr/bin/env python3
"""
Build a clean root/form index from ግስ ከሀ-ፐ raw page text.

Reads:  data/sources/giss_keha_pe_raw.json
Writes: data/grammar_index.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "sources" / "giss_keha_pe_raw.json"
OUT_PATH = ROOT / "data" / "grammar_index.json"

PATTERN_CODES = ("ቀተ", "ቀደ", "ጦመ", "ተን", "ባረ", "ማህ", "ሴሰ", "ክህ", "ርዕስ")
PATTERN_ALT = "|".join(PATTERN_CODES)
ROOT_RE = r"[ሀ-ፐ]{3,4}"

PATTERN_SUFFIX_RE = re.compile(rf"({'|'.join(PATTERN_CODES)})$")
ROOT_HEAD_RE = re.compile(rf"^({ROOT_RE})")
BLOCK_RE = re.compile(rf"({ROOT_RE})({PATTERN_ALT})----")
TAIL_BLOCK_RE = re.compile(rf"([ሀ-ፐ]{{0,12}})({ROOT_RE})({PATTERN_ALT})----")
ALT_ROOT_RE = re.compile(rf"/({ROOT_RE})/")
GLOSS_OVERRIDES = {
    "ንገረ": "እሽኰኰ አለ",
    "ሐወረ": "ሖረ",
    "ሐውረ": "ሖረ",
}

FORM_ROOT_ALIASES = {
    "ሐውረ": "ሐወረ",
}

GLOSS_SPLIT_RE = re.compile(r"[,፣/]")


def peel_root_header(header: str) -> tuple[str | None, str | None]:
    header = header.strip(" -")
    if not header:
        return None, None
    first_alt = header.split("/")[0].strip()
    match = PATTERN_SUFFIX_RE.search(first_alt)
    if match:
        root = first_alt[: match.start()].strip(" -/")
        if ROOT_HEAD_RE.fullmatch(root):
            return root, match.group(1)
    head = ROOT_HEAD_RE.match(first_alt)
    if head:
        return head.group(1), None
    return None, None


def clean_gloss(text: str) -> str:
    text = text.strip(" -/()")
    if not text:
        return ""
    if " " in text:
        text = text.split()[0]
    parts = [p.strip() for p in GLOSS_SPLIT_RE.split(text) if p.strip()]
    for part in parts:
        if 2 <= len(part) <= 32 and not part.endswith(tuple(PATTERN_CODES)):
            return part
    return parts[0] if parts else text[:32]


def first_gloss_after_marker(text: str, marker_end: int) -> str:
    tail = text[marker_end:]
    stop = len(tail)
    for sep in ("----", "---", "--"):
        idx = tail.find(sep)
        if idx >= 0:
            stop = min(stop, idx)
    return clean_gloss(tail[:stop])


def add_root(
    roots: dict,
    form_lookup: dict,
    *,
    root: str,
    page: int,
    pattern: str | None = None,
    gloss: str | None = None,
    forms: list[str] | None = None,
) -> None:
    if not root or not ROOT_HEAD_RE.fullmatch(root):
        return
    bucket = roots.setdefault(root, {
        "root": root,
        "patterns": set(),
        "glosses": set(),
        "forms": set(),
        "pages": set(),
    })
    bucket["pages"].add(page)
    if pattern:
        bucket["patterns"].add(pattern)
    if gloss:
        bucket["glosses"].add(gloss)
    for form in forms or []:
        if form and form != root:
            bucket["forms"].add(form)
            form_lookup.setdefault(form, [])
            if root not in form_lookup[form]:
                form_lookup[form].append(root)


def parse_page(text: str, page_num: int, roots: dict, form_lookup: dict) -> None:
    section_roots: list[str] = []

    for section in text.split("❖")[1:]:
        first_break = section.find("----")
        header = section[:first_break] if first_break >= 0 else section[:48]
        root, header_pattern = peel_root_header(header)
        if root:
            section_roots.append(root)
            gloss = first_gloss_after_marker(section, len(header.lstrip()))
            add_root(
                roots, form_lookup,
                root=root, page=page_num, pattern=header_pattern, gloss=gloss or None,
            )
            for alt in ALT_ROOT_RE.findall(header):
                add_root(
                    roots, form_lookup,
                    root=alt, page=page_num, pattern=header_pattern, forms=[root],
                )

    for match in BLOCK_RE.finditer(text):
        root, pattern = match.group(1), match.group(2)
        gloss = first_gloss_after_marker(text, match.end())
        add_root(
            roots, form_lookup,
            root=root, page=page_num, pattern=pattern, gloss=gloss or None,
        )

    for match in TAIL_BLOCK_RE.finditer(text):
        prefix, root, pattern = match.group(1), match.group(2), match.group(3)
        gloss = first_gloss_after_marker(text, match.end())
        add_root(
            roots, form_lookup,
            root=root, page=page_num, pattern=pattern, gloss=gloss or None,
            forms=[prefix + root] if prefix else None,
        )

    for alt in ALT_ROOT_RE.findall(text):
        alias = FORM_ROOT_ALIASES.get(alt, alt)
        add_root(roots, form_lookup, root=alias, page=page_num, forms=[alt])


def build_index(raw_payload: dict) -> dict:
    roots: dict = {}
    form_lookup: dict = {}

    for page in raw_payload.get("pageTexts", []):
        parse_page(page.get("text", ""), page.get("page", 0), roots, form_lookup)

    root_list = []
    for root, data in sorted(roots.items()):
        glosses = sorted(data["glosses"], key=len)
        primary = GLOSS_OVERRIDES.get(root) or (glosses[0] if glosses else None)
        root_list.append({
            "root": root,
            "primary_gloss": primary,
            "glosses": glosses[:12],
            "patterns": sorted(data["patterns"]),
            "forms": sorted(data["forms"])[:32],
            "pages": sorted(data["pages"]),
        })

    return {
        "source": raw_payload.get("title", "ግስ ከሀ-ፐ"),
        "author": raw_payload.get("author", "Ermias Gashu"),
        "url": raw_payload.get("url"),
        "total_pages": raw_payload.get("totalPages"),
        "root_count": len(root_list),
        "roots": root_list,
        "form_to_roots": form_lookup,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=RAW_PATH)
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    raw_payload = json.loads(args.input.read_text(encoding="utf-8"))
    index = build_index(raw_payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.output} ({index['root_count']} roots)")


if __name__ == "__main__":
    main()
