"""Deep test of the repaired analyzer against lexicon ground truth.

For each of the 3,846 roots in lexicon.json, generate real conjugated
surface forms with the conjugator, then run the repaired extract_root
on each form and check whether the true root is recovered.

This is a consistency test (round-trip validation): it checks that the
analyzer and conjugator agree on the morphological system, not that the
system matches external linguistic ground truth. The stemmer does
genuine morphological analysis (affix stripping, skeleton extraction,
weak-consonant restoration) and does not do surface-form lookup.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.stemmer import GeezStemmer
from src.conjugator import EthioMorphGenerator
from src.normalizer import normalize_geez
from src.decomposer import get_consonant_skeleton


def load_roots():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "lexicon.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["roots"]


def generate_forms(gen, root, verb_type):
    """Generate a small set of representative surface forms for a root."""
    forms = []
    # (tense, subject) pairs covering the main paradigms
    paradigms = [
        ("perfective", "3sm"),
        ("perfective", "3sf"),
        ("imperfective", "3sm"),
        ("imperfective", "3pm"),
        ("jussive", "3sm"),
        ("imperative", "2sm"),
    ]
    for tense, subj in paradigms:
        try:
            out = gen.generate_word(root, tense, subj, verb_type=verb_type)
        except Exception:
            continue
        if isinstance(out, dict) and "word" in out and out["word"]:
            forms.append((out["word"], tense, subj))
    return forms


def main():
    roots = load_roots()
    print(f"Loaded {len(roots)} lexicon roots")

    gen = EthioMorphGenerator()
    stemmer = GeezStemmer()

    total_forms = 0
    correct = 0
    generated_ok = 0
    by_type = {}
    failures = []

    for entry in roots:
        root = entry["root"]
        rtype = entry.get("type", "unknown")
        by_type.setdefault(rtype, {"forms": 0, "correct": 0})

        forms = generate_forms(gen, root, rtype)
        if not forms:
            continue
        generated_ok += 1

        norm_true = normalize_geez(root)
        true_skel = get_consonant_skeleton(norm_true)
        for word, tense, subj in forms:
            total_forms += 1
            by_type[rtype]["forms"] += 1
            try:
                res = stemmer.extract_root(word)
            except Exception as e:
                failures.append((word, root, f"EXC {e}"))
                continue
            pred = res.get("root")
            # Compare consonantal skeletons: Ge'ez roots are consonantal,
            # vowel orders in the citation form are not contrastive.
            pred_skel = get_consonant_skeleton(normalize_geez(pred)) if pred else None
            if pred_skel == true_skel:
                correct += 1
                by_type[rtype]["correct"] += 1
            else:
                failures.append((word, root, pred))

    print(f"\nRoots with generated forms: {generated_ok}/{len(roots)}")
    print(f"Total surface forms tested: {total_forms}")
    print(f"Correct root recovery: {correct}/{total_forms} = {100.0*correct/max(total_forms,1):.1f}%")
    print("\nBy root type:")
    for rtype, st in sorted(by_type.items(), key=lambda x: -x[1]["forms"]):
        f, c = st["forms"], st["correct"]
        if f:
            print(f"  {rtype:20s} {c:5d}/{f:5d} = {100.0*c/f:5.1f}%")
    print(f"\nFailure sample (first 30 of {len(failures)}):")
    for word, true_root, pred in failures[:30]:
        print(f"  {word}  true={true_root}  pred={pred}")

    # Save full failure list for analysis
    out_path = os.path.join(os.path.dirname(__file__), "..", "lexicon_test_failures.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            [{"word": w, "true_root": t, "predicted": p} for w, t, p in failures],
            f, ensure_ascii=False, indent=1,
        )
    print(f"\nFull failure list: {out_path}")


if __name__ == "__main__":
    main()
