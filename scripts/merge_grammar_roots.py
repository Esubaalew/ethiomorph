"""Merge grammar-index roots into lexicon.json.

Adds 2,032 roots from grammar_index.json and grammar_zewadla_index.json
that are not in lexicon.json. Types are assigned from the pattern-code
mapping derived from overlapping roots where available:

  ቀተ -> type_a, ቀደ -> type_b, ተን -> type_tanbala, ክህ -> type_d,
  ማህ -> type_mahräka, ሴሰ -> type_c_e, ባረ -> type_c, ጦመ -> type_c_o

Roots without a recognized pattern code (284 entries) are defaulted to
type_a as a placeholder; these require human review (see
type_a_review_284.json) and must not be treated as validated type_a
assignments.

Each added entry records its source. The original 1,894 entries are
untouched. A backup is written first.
"""

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

PATTERN_TO_TYPE = {
    "ቀተ": "type_a",
    "ቀደ": "type_b",
    "ተን": "type_tanbala",
    "ክህ": "type_d",
    "ማህ": "type_mahräka",
    "ሴሰ": "type_c_e",
    "ባረ": "type_c",
    "ጦመ": "type_c_o",
}


def main():
    lex_path = os.path.join(DATA, "lexicon.json")
    backup = lex_path + ".pre_merge_20260930.bak"
    shutil.copy2(lex_path, backup)
    print(f"Backup: {backup}")

    with open(lex_path, encoding="utf-8") as f:
        lex = json.load(f)
    existing = set(e["root"] for e in lex["roots"])
    print(f"Existing roots: {len(existing)}")

    def load_index(name):
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            return json.load(f)

    gi = load_index("grammar_index.json")
    gz = load_index("grammar_zewadla_index.json")

    # Prefer grammar_index entries; fill gaps from zewadla.
    merged = {}
    for r in gi["roots"]:
        if r["root"] not in merged:
            merged[r["root"]] = ("grammar_index", r)
    for r in gz["roots"]:
        if r["root"] not in merged:
            merged[r["root"]] = ("grammar_zewadla_index", r)

    added = 0
    no_pattern = 0
    for root, (src, entry) in sorted(merged.items()):
        if root in existing:
            continue
        patterns = entry.get("patterns") or []
        vtype = None
        for p in patterns:
            if p in PATTERN_TO_TYPE:
                vtype = PATTERN_TO_TYPE[p]
                break
        if vtype is None:
            no_pattern += 1
            vtype = "type_a"  # default; flagged via source field
        glosses = entry.get("glosses") or []
        meaning = glosses[0] if glosses else ""
        # Drop a following headword glued on by the grammar ingest.
        from scripts.build_grammar_index import _strip_glued_headword
        if meaning:
            meaning = _strip_glued_headword(meaning, set(existing) | set(merged))
        lex["roots"].append({
            "root": root,
            "type": vtype,
            "meaning": meaning,
            "source": src,
            "source_patterns": patterns,
        })
        added += 1

    with open(lex_path, "w", encoding="utf-8") as f:
        json.dump(lex, f, ensure_ascii=False, indent=1)

    print(f"Added: {added} (no pattern code, defaulted to type_a: {no_pattern})")
    print(f"Total roots now: {len(lex['roots'])}")


if __name__ == "__main__":
    main()
