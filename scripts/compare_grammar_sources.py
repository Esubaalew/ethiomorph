#!/usr/bin/env python3
"""
Compare ግስ ከሀ-ፐ and መጽሐፈ ግስ ዘዋድላ indices against each other and lexicon.json.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GISS_PATH = ROOT / "data" / "grammar_index.json"
ZEW_PATH = ROOT / "data" / "grammar_zewadla_index.json"
LEX_PATH = ROOT / "data" / "lexicon.json"
OUT_PATH = ROOT / "data" / "grammar_compare_report.json"

KEY_ROOTS = [
    "ንገረ", "ነገረ", "ሐወረ", "ሀልሀ", "ኀጥአ", "ኰነነ",
    "ቃሕቅሐ", "ጠረሰ", "ሰርሐ", "ብህለ", "ሐንገረ", "ሖረ",
]

NOISY_GLOSS_RE = re.compile(r"^.{1,2}$|❖")


def load_map(path: Path, field: str = "primary_gloss") -> dict[str, str | None]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {e["root"]: e.get(field) for e in payload.get("roots", [])}


def tokens(s: str | None) -> set[str]:
    if not s:
        return set()
    return {t.strip() for t in re.split(r"[,፣/;\s]+", s) if t.strip()}


def gloss_compatible(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return True
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return True
    if ta & tb:
        return True
    na = "".join(sorted(ta))
    nb = "".join(sorted(tb))
    return na in nb or nb in na


def is_noisy(gloss: str | None) -> bool:
    if not gloss:
        return True
    return bool(NOISY_GLOSS_RE.match(gloss.strip()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    giss = load_map(GISS_PATH)
    zew = load_map(ZEW_PATH)
    lex_payload = json.loads(LEX_PATH.read_text(encoding="utf-8"))
    lex = {e["root"]: e.get("meaning") for e in lex_payload.get("roots", [])}

    overlap = sorted(set(giss) & set(zew))
    only_giss = sorted(set(giss) - set(zew))
    only_zew = sorted(set(zew) - set(giss))

    conflicts = []
    zew_fixes_giss = []
    for root in overlap:
        gg, zg, lg = giss.get(root), zew.get(root), lex.get(root)
        if not gloss_compatible(gg, zg):
            conflicts.append({
                "root": root,
                "giss": gg,
                "zewadla": zg,
                "lexicon": lg,
            })
        if is_noisy(gg) and zg and not is_noisy(zg):
            zew_fixes_giss.append({
                "root": root,
                "giss_gloss": gg,
                "zewadla_gloss": zg,
                "lexicon": lg,
            })

    key_checks = {}
    for root in KEY_ROOTS:
        key_checks[root] = {
            "giss": giss.get(root),
            "zewadla": zew.get(root),
            "lexicon": lex.get(root),
            "giss_zewadla_agree": gloss_compatible(giss.get(root), zew.get(root)),
        }

    report = {
        "giss_roots": len(giss),
        "zewadla_roots": len(zew),
        "overlap": len(overlap),
        "only_giss_count": len(only_giss),
        "only_zewadla_count": len(only_zew),
        "conflicts_count": len(conflicts),
        "zewadla_fixes_noisy_giss_count": len(zew_fixes_giss),
        "key_roots": key_checks,
        "conflicts_sample": conflicts[:40],
        "zewadla_fixes_sample": zew_fixes_giss[:40],
        "only_zewadla_sample": only_zew[:30],
        "only_giss_sample": only_giss[:30],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Giss: {len(giss)} | Zewadla: {len(zew)} | Overlap: {len(overlap)}")
    print(f"Conflicts: {len(conflicts)} | Zewadla fixes noisy giss: {len(zew_fixes_giss)}")
    print("\nKey roots:")
    for root, data in key_checks.items():
        status = "OK" if data["giss_zewadla_agree"] else "DIFF"
        print(f"  [{status}] {root}: giss={data['giss']!r} zew={data['zewadla']!r} lex={data['lexicon']!r}")
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
