"""Curate the geezRPA lexicon to fix the stem-as-root systematic error.

Problem: the grammar-index merge added derived stems as lexicon headwords
(e.g. teqebele alongside base root qebele). The analyzer's direct
lexicon-hit preference then returns the stem verbatim instead of stripping
to the base root, causing source-attested validation misses.

Policy (documented here, applied below):
  For each derived-stem entry E with book-attested base root B:
  (a) REMOVE E if the base root B is in the lexicon AND the analyzer,
      with E removed, recovers B for surface form E (empirically tested).
      This is safe: the analyzer's own affix-stripping covers the derivation.
  (b) KEEP E but annotate it with "base_root": B if removal would lose
      coverage (analyzer cannot recover B, e.g. reduplicated stems).
      The stemmer consults this annotation to map derived stems to their
      base roots during analysis.
  Entries are never silently dropped: every change is logged with a reason.
  Orthographic variants (same skeleton) are NOT derived stems and are left alone.
  Book-mapping noise (no morphological relationship between E and B) is excluded.

Additionally applies the human-reviewed 284 type_a verdicts and merges the
17 staged roots (provenance preserved).
"""

import copy
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.decomposer import get_consonant_skeleton
from src.normalizer import normalize_geez
from src.stemmer import GeezStemmer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")

DERIV_PREFIXES = ("ተ", "አ", "አን", "አስ", "ተስ", "ዐ")


def skel(s):
    try:
        return get_consonant_skeleton(normalize_geez(s)) if s else None
    except Exception:
        return None


def load_lexicon(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_book_mapping():
    """form -> roots, grammar_index plus cleaned zewadla (same as validator)."""
    gi = json.load(open(os.path.join(DATA, "grammar_index.json"), encoding="utf-8"))
    gz = json.load(open(os.path.join(DATA, "grammar_zewadla_index.json"), encoding="utf-8"))
    ftr = dict(gi["form_to_roots"])
    forms2 = set()
    for r in gz["roots"]:
        forms2.update(r.get("forms", []))
    codes = {"ቀተ", "ቀደ", "ተን", "ክህ", "ማህ", "ሴሰ", "ባረ", "ጦመ"}
    for k, v in gz["form_to_roots"].items():
        if k in forms2 and k not in codes and k not in ftr:
            ftr[k] = v
    return ftr


def morphological_relation(E, B):
    """Return the derivational relationship of E to B, or None.

    E is the candidate derived stem, B the base root. Checks clear
    derivational affixation; returns a label like 'ተ+base', 'አ+base',
    'reduplication', 'affixation', or None if no plausible relation.
    """
    skE, skB = skel(E), skel(B)
    if not skE or not skB or skE == skB:
        return None
    # Clear derivational prefixes: strip prefix chars, compare skeletons.
    for aff in DERIV_PREFIXES:
        if E.startswith(aff) and len(E) > len(aff):
            if skel(E[len(aff):]) == skB:
                return aff + "+base"
    # General affixation: B's skeleton is a proper contiguous subsequence
    # of E's skeleton (covers reduplication and complex prefixes).
    if skB in skE and len(skE) > len(skB):
        # Reduplication check: E's skeleton shows repeated material.
        if len(skE) >= 2 * len(skB) - 1:
            return "reduplication/complex"
        return "affixation"
    return None


# ---------------------------------------------------------------------------
# Stage 1: apply the human-reviewed 284 type_a verdicts
# ---------------------------------------------------------------------------

PATTERN_CODE_TO_TYPE = {
    "ቀተ": "type_a", "ቀደ": "type_b", "ተን": "type_tanbala", "ክህ": "type_d",
    "ማህ": "type_mahräka", "ሴሰ": "type_c_e", "ባረ": "type_c", "ጦመ": "type_c_o",
}


def apply_284_review(lex, log):
    review = json.load(open(os.path.join(REPO, "type_a_review_284.json"), encoding="utf-8"))
    by_root = {e["root"]: e for e in lex["roots"]}
    counts = {"reassigned": 0, "unknown": 0, "removed": 0, "base_added": 0, "skipped": 0}
    for item in review:
        R = item["root"]
        verdict = item["verdict"]
        entry = by_root.get(R)
        if verdict == "reassigned":
            if entry is None:
                log.append({"action": "284_reassign_skipped", "root": R,
                            "reason": "entry not in lexicon"})
                counts["skipped"] += 1
                continue
            old = entry.get("type")
            entry["type"] = item["suggested"]
            log.append({"action": "284_reassign", "root": R,
                        "old_type": old, "new_type": item["suggested"],
                        "reason": item["detail"]})
            counts["reassigned"] += 1
        elif verdict == "genuinely_unknown":
            if entry is None:
                log.append({"action": "284_unknown_skipped", "root": R,
                            "reason": "entry not in lexicon"})
                counts["skipped"] += 1
                continue
            old = entry.get("type")
            entry["type"] = "unknown"
            log.append({"action": "284_mark_unknown", "root": R, "old_type": old,
                        "reason": item["detail"]})
            counts["unknown"] += 1
        elif verdict == "artifact_remove":
            # Parse "remove; stripped root X already/NOT in lexicon[, suggested type T if validated]"
            m = re.search(r"stripped root (\S+) (already|NOT) in lexicon", item["suggested"])
            if not m:
                log.append({"action": "284_artifact_skipped", "root": R,
                            "reason": "unparseable suggested field: " + item["suggested"]})
                counts["skipped"] += 1
                continue
            base, presence = m.group(1), m.group(2)
            t = re.search(r"suggested type (\S+)", item["suggested"])
            suggested_type = t.group(1) if t else None
            if entry is not None:
                lex["roots"].remove(entry)
                del by_root[R]
                log.append({"action": "284_artifact_removed", "root": R,
                            "stripped_base": base, "base_in_lexicon": presence == "already",
                            "reason": item["detail"]})
                counts["removed"] += 1
            else:
                log.append({"action": "284_artifact_not_found", "root": R,
                            "reason": "entry not in lexicon"})
                counts["skipped"] += 1
            if presence == "NOT":
                # The stripped base carries unique information (meaning + pattern
                # code). Re-add it as a proper root so nothing is lost.
                if base not in by_root:
                    # Derive type from the pattern code suffix on the artifact.
                    vtype = suggested_type
                    if not vtype:
                        for code, tp in PATTERN_CODE_TO_TYPE.items():
                            if R.endswith(code):
                                vtype = tp
                                break
                    new_entry = {
                        "root": base,
                        "type": vtype or "unknown",
                        "meaning": item.get("meaning") or "",
                        "provenance": {
                            "derived_from": "pattern-code artifact stripped during curation",
                            "artifact": R,
                            "source": item.get("source"),
                            "date": "2026-10-01",
                        },
                    }
                    lex["roots"].append(new_entry)
                    by_root[base] = new_entry
                    log.append({"action": "284_base_added", "root": base,
                                "from_artifact": R, "type": vtype,
                                "reason": "stripped base was not in lexicon; "
                                          "added to preserve unique information"})
                    counts["base_added"] += 1
                else:
                    log.append({"action": "284_base_already_present", "root": base,
                                "from_artifact": R})
    return counts


# ---------------------------------------------------------------------------
# Stage 2: derived-stem curation with empirical removal test
# ---------------------------------------------------------------------------

class LexiconTester:
    """Wraps a GeezStemmer to test entry removal without touching disk."""

    def __init__(self):
        self.st = GeezStemmer()

    def _remove(self, E):
        st = self.st
        saved = {}
        if E in st.lexicon_roots:
            saved["entry"] = st.lexicon_roots.pop(E)
        norm = normalize_geez(E)
        if st.lexicon_normalized_lookup.get(norm) == E:
            saved["norm"] = norm
            del st.lexicon_normalized_lookup[norm]
        sk = normalize_geez(get_consonant_skeleton(E))
        lst = st.skeleton_lookup.get(sk, [])
        if E in lst:
            saved["skel"] = (sk, list(lst))
            lst.remove(E)
            if not lst:
                del st.skeleton_lookup[sk]
        for attr in ("weak_initial_roots", "hollow_w_roots", "hollow_y_roots",
                     "quadriliterals"):
            s = getattr(st, attr, None)
            if s is not None and E in s:
                saved[attr] = True
                s.remove(E)
        for attr in ("hollow_w_lookup", "hollow_y_lookup"):
            d = getattr(st, attr, None)
            if d and d.get(norm) == E:
                saved[attr] = norm
                del d[norm]
        return saved

    def _restore(self, E, saved):
        st = self.st
        if "entry" in saved:
            st.lexicon_roots[E] = saved["entry"]
        if "norm" in saved:
            st.lexicon_normalized_lookup[saved["norm"]] = E
        if "skel" in saved:
            sk, lst = saved["skel"]
            st.skeleton_lookup[sk] = lst
        for attr in ("weak_initial_roots", "hollow_w_roots", "hollow_y_roots",
                     "quadriliterals"):
            if saved.get(attr):
                getattr(st, attr).add(E)
        for attr in ("hollow_w_lookup", "hollow_y_lookup"):
            if attr in saved:
                getattr(st, attr)[saved[attr]] = E

    def recovers_base(self, E, B):
        """True if, with E removed, extract_root(E) returns B (skeleton match)."""
        saved = self._remove(E)
        try:
            res = self.st.extract_root(E)
            pred = res.get("root")
            return skel(pred) == skel(B) if pred else False
        except Exception:
            return False
        finally:
            self._restore(E, saved)


def curate_derived_stems(lex, log):
    # Persist the Stage-1 lexicon first so the empirical removal test runs
    # against the post-284-review inventory (type changes can affect routing).
    lex_path = os.path.join(DATA, "lexicon.json")
    with open(lex_path, "w", encoding="utf-8") as f:
        json.dump(lex, f, ensure_ascii=False, indent=1)

    ftr = load_book_mapping()
    by_root = {e["root"]: e for e in lex["roots"]}
    rset = set(by_root)
    candidates = []  # (E, B, relation)
    for e in lex["roots"]:
        R = e["root"]
        mapped = ftr.get(R)
        if not mapped:
            continue
        for b in mapped:
            if b in rset and b != R and skel(b) != skel(R):
                rel = morphological_relation(R, b)
                if rel:
                    candidates.append((R, b, rel))
                break
    print(f"derived-stem candidates: {len(candidates)}")
    tester = LexiconTester()
    redirect = {}  # removed stem -> ultimate base (for chains like A->B->C)
    counts = {"removed": 0, "annotated": 0, "skipped_chain": 0}
    for E, B, rel in candidates:
        entry = by_root.get(E)
        if entry is None:
            continue  # already handled
        B_resolved = redirect.get(B, B)
        if B_resolved not in by_root:
            # Base was removed earlier in this pass; re-resolve or skip.
            log.append({"action": "derived_stem_skipped", "root": E,
                        "base_root": B, "relation": rel,
                        "reason": "base root no longer in lexicon after earlier "
                                  "removal; left untouched"})
            counts["skipped_chain"] += 1
            continue
        if tester.recovers_base(E, B_resolved):
            lex["roots"].remove(entry)
            del by_root[E]
            rset.discard(E)
            redirect[E] = B_resolved
            log.append({"action": "derived_stem_removed", "root": E,
                        "base_root": B_resolved, "relation": rel,
                        "book_base": B,
                        "reason": "book maps form to base root; analyzer recovers "
                                  "base root after removal (policy a)"})
            counts["removed"] += 1
        else:
            entry["base_root"] = B_resolved
            entry["derivation_note"] = (
                f"derived stem of {B_resolved} ({rel}); analyzer cannot yet strip to "
                f"base, kept for coverage pending analyzer update (policy b)")
            log.append({"action": "derived_stem_annotated", "root": E,
                        "base_root": B_resolved, "relation": rel,
                        "reason": "book maps form to base root but analyzer does "
                                  "not recover base after removal; kept with "
                                  "base_root annotation (policy b)"})
            counts["annotated"] += 1
    return counts, len(candidates)


# ---------------------------------------------------------------------------
# Stage 3: merge the 17 staged roots
# ---------------------------------------------------------------------------

def merge_staged(lex, log):
    st = json.load(open(os.path.join(DATA, "new_roots_staging.json"), encoding="utf-8"))
    staged = st["roots"]
    existing_skels = {skel(e["root"]) for e in lex["roots"]}
    existing_roots = {e["root"] for e in lex["roots"]}
    counts = {"added": 0, "skipped_collision": 0}
    for r in staged:
        root = r["root"]
        if root in existing_roots or skel(root) in existing_skels:
            log.append({"action": "staged_skipped_collision", "root": root,
                        "reason": "root or skeleton already in lexicon"})
            counts["skipped_collision"] += 1
            continue
        entry = {
            "root": root,
            "type": r.get("type", "unknown"),
            "meaning": r.get("meaning") or "",
            "provenance": r.get("provenance") or {},
            "attestation": r.get("attestation"),
            "staged_method": r.get("method"),
        }
        lex["roots"].append(entry)
        existing_roots.add(root)
        existing_skels.add(skel(root))
        log.append({"action": "staged_root_added", "root": root,
                    "type": entry["type"],
                    "provenance": entry["provenance"],
                    "reason": "merged from new_roots_staging.json; no collision"})
        counts["added"] += 1
    return counts


def main():
    lex_path = os.path.join(DATA, "lexicon.json")
    backup = lex_path + ".pre_curation_20261001.bak"
    if not os.path.exists(backup):
        shutil.copy2(lex_path, backup)
        print("backup:", backup)
    else:
        print("backup already exists:", backup)

    lex = load_lexicon(lex_path)
    n_before = len(lex["roots"])
    print("entries before:", n_before)
    log = []

    c1 = apply_284_review(lex, log)
    print("284 review:", c1)

    c2, n_cand = curate_derived_stems(lex, log)
    print("derived stems:", c2)

    c3 = merge_staged(lex, log)
    print("staged merge:", c3)

    n_after = len(lex["roots"])
    print("entries after:", n_after)

    with open(lex_path, "w", encoding="utf-8") as f:
        json.dump(lex, f, ensure_ascii=False, indent=1)
    log_path = os.path.join(REPO, "lexicon_curation_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": "2026-10-01",
            "policy": __doc__,
            "entries_before": n_before,
            "entries_after": n_after,
            "review_284": c1,
            "derived_stem_candidates": n_cand,
            "derived_stems": c2,
            "staged_merge": c3,
            "changes": log,
        }, f, ensure_ascii=False, indent=1)
    print("wrote", lex_path)
    print("wrote", log_path)


if __name__ == "__main__":
    main()
