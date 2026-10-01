"""Assign types to the 44 unknown-type lexicon entries (2026-10-01).

- Removes የቤት (genitive phrase 'of the house', extraction artifact, not a verb root).
- Assigns type_a to 27 genuinely-unknown triliteral verbs (unmarked G-stem default;
  analyzer already treats 'unknown' like 'type_a' in disambiguation).
- Assigns type_a to 15 triliteral staged Hailay roots.
- Assigns quadriliteral to ሠርገወ (4 consonants).
- Leaves ማዕጾ as unknown with a review flag (nominal ma- prefix, no meaning;
  needs Esube's judgment).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from decomposer import get_consonant_skeleton
from normalizer import normalize_geez

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
LEX_PATH = os.path.join(BASE, "lexicon.json")

REMOVE = {"የቤት"}  # genitive phrase, not a verb root
QUADRILITERAL = {"ሠርገወ"}
NEEDS_REVIEW = {"ማዕጾ"}


def main():
    with open(LEX_PATH, encoding="utf-8") as f:
        lex = json.load(f)
    roots = lex["roots"]
    log = []

    kept = []
    for e in roots:
        r = e["root"]
        if r in REMOVE:
            log.append({"root": r, "action": "removed",
                        "reason": "genitive phrase 'of the house', not a verb root; extraction artifact"})
            continue
        if e.get("type") != "unknown":
            kept.append(e)
            continue
        if r in NEEDS_REVIEW:
            e["review_flag"] = ("nominal ma- prefix, no meaning; human-curated but "
                                "likely noun, needs Esube review before type assignment")
            log.append({"root": r, "action": "flagged_for_review",
                        "reason": e["review_flag"]})
            kept.append(e)
            continue
        skel = get_consonant_skeleton(normalize_geez(r))
        n_cons = len(skel)
        if r in QUADRILITERAL or n_cons == 4:
            e["type"] = "quadriliteral"
            e["type_assigned"] = "2026-10-01: 4-consonant skeleton"
        elif n_cons == 3:
            e["type"] = "type_a"
            e["type_assigned"] = "2026-10-01: triliteral default (unmarked G-stem)"
        else:
            e["review_flag"] = f"unexpected skeleton length {n_cons}, needs review"
            log.append({"root": r, "action": "flagged_for_review",
                        "reason": e["review_flag"]})
        log.append({"root": r, "action": "type_assigned", "type": e["type"],
                    "skeleton": skel})
        kept.append(e)

    lex["roots"] = kept
    with open(LEX_PATH, "w", encoding="utf-8") as f:
        json.dump(lex, f, ensure_ascii=False, indent=2)

    with open(os.path.join(BASE, "unknown_type_assignment_log.json"), "w",
              encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    remaining = [e["root"] for e in kept if e.get("type") == "unknown"]
    print(f"assigned: {sum(1 for x in log if x['action'] == 'type_assigned')}")
    print(f"removed: {sum(1 for x in log if x['action'] == 'removed')}")
    print(f"flagged: {sum(1 for x in log if x['action'] == 'flagged_for_review')}")
    print(f"remaining unknown: {len(remaining)} {remaining}")


if __name__ == "__main__":
    main()
