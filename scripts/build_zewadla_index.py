#!/usr/bin/env python3
"""
Build root index from መጽሐፈ ግስ ዘዋድላ ምስለ ስምዕ raw page text.

Reads:  data/sources/zewadla_giss_raw.json
Writes: data/grammar_zewadla_index.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "sources" / "zewadla_giss_raw.json"
OUT_PATH = ROOT / "data" / "grammar_zewadla_index.json"

PATTERN_CODES = ("ቀተ", "ቀደ", "ጦመ", "ተን", "ባረ", "ማህ", "ሴሰ", "ክህ", "ርዕስ")
PATTERN_ALT = "|".join(PATTERN_CODES)
ROOT_RE = r"[ሀ-ፐ]{3,4}"

PATTERN_SUFFIX_RE = re.compile(rf"({'|'.join(PATTERN_CODES)})$")
ROOT_HEAD_RE = re.compile(rf"^({ROOT_RE})")
ENTRY_RE = re.compile(
    rf"(\d+)\)\s*([^፤]+?)\s*-\s*([^፤]+)",
)
FORM_SPLIT_RE = re.compile(r"[,፣]")
GLOSS_SPLIT_RE = re.compile(r"[,፣/]")
SYNONYM_RE = re.compile(r"ምስክር-\s*([^፤]+)")

GLOSS_OVERRIDES = {
    "ንገረ": "እሽኰኰ አለ",
    "ሐንገረ": "እሽኰኰ አለ",
    "ሐወረ": "ሔደ",
    "ሐውረ": "ሔደ",
    "ሖረ": "ሔደ",
}

FORM_ROOT_ALIASES = {
    "ሐውረ": "ሐወረ",
    "ሖረ": "ሐወረ",
    "ሐንገረ": "ንገረ",
}


def peel_form(form: str) -> tuple[str | None, str | None]:
    form = form.strip(" -/")
    if not form:
        return None, None
    match = PATTERN_SUFFIX_RE.search(form)
    if match:
        root = form[: match.start()].strip(" -/")
        if ROOT_HEAD_RE.fullmatch(root):
            return root, match.group(1)
    head = ROOT_HEAD_RE.match(form)
    if head:
        return head.group(1), None
    return None, None


def clean_gloss(text: str) -> str:
    text = text.strip(" -/()")
    if not text:
        return ""
    parts = [p.strip() for p in GLOSS_SPLIT_RE.split(text) if p.strip()]
    for part in parts:
        if 2 <= len(part) <= 48 and not part.endswith(tuple(PATTERN_CODES)):
            return part
    return parts[0] if parts else text[:48]


def add_root(
    roots: dict,
    form_lookup: dict,
    *,
    root: str,
    page: int,
    pattern: str | None = None,
    gloss: str | None = None,
    forms: list[str] | None = None,
    synonyms: list[str] | None = None,
) -> None:
    if not root or not ROOT_HEAD_RE.fullmatch(root):
        return
    root = FORM_ROOT_ALIASES.get(root, root)
    bucket = roots.setdefault(root, {
        "root": root,
        "patterns": set(),
        "glosses": set(),
        "synonyms": set(),
        "forms": set(),
        "pages": set(),
    })
    bucket["pages"].add(page)
    if pattern:
        bucket["patterns"].add(pattern)
    if gloss:
        bucket["glosses"].add(gloss)
    for syn in synonyms or []:
        if syn:
            bucket["synonyms"].add(syn)
    for form in forms or []:
        if form and form != root:
            bucket["forms"].add(form)
            form_lookup.setdefault(form, [])
            if root not in form_lookup[form]:
                form_lookup[form].append(root)


def parse_entry_forms(forms_blob: str) -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    for chunk in FORM_SPLIT_RE.split(forms_blob):
        chunk = chunk.strip()
        if not chunk:
            continue
        root, pattern = peel_form(chunk)
        if root:
            out.append((root, pattern))
    return out


def parse_page(text: str, page_num: int, roots: dict, form_lookup: dict) -> None:
    for match in ENTRY_RE.finditer(text):
        forms_blob = match.group(2).strip()
        gloss_blob = match.group(3).strip()
        gloss = clean_gloss(gloss_blob.split("ምስክር-")[0])
        synonyms = [clean_gloss(s) for s in SYNONYM_RE.findall(gloss_blob)]
        parsed_forms = parse_entry_forms(forms_blob)
        if not parsed_forms:
            continue
        primary_root, primary_pattern = parsed_forms[0]
        all_forms = [f for f, _ in parsed_forms]
        add_root(
            roots,
            form_lookup,
            root=primary_root,
            page=page_num,
            pattern=primary_pattern,
            gloss=gloss or None,
            forms=all_forms,
            synonyms=synonyms,
        )
        for alt_root, alt_pattern in parsed_forms[1:]:
            add_root(
                roots,
                form_lookup,
                root=alt_root,
                page=page_num,
                pattern=alt_pattern,
                gloss=gloss or None,
                forms=[primary_root],
                synonyms=synonyms,
            )


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
            "synonyms": sorted(data["synonyms"])[:16],
            "patterns": sorted(data["patterns"]),
            "forms": sorted(data["forms"])[:32],
            "pages": sorted(data["pages"]),
        })

    return {
        "source": raw_payload.get("title", "መጽሐፈ ግስ ዘዋድላ ምስለ ስምዕ"),
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
