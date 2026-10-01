"""Source-attested validation of the Ge'ez analyzer (task 1).

Uses ONLY grammar-book forms (form_to_roots from the two grammar indexes),
never conjugator output. For each form the analyzer predicts a root; a hit
means the predicted root's consonantal skeleton matches the book-attested
root's skeleton.

The analyzer has a grammar-form fallback path (method == 'grammar_form')
that consults the same form_to_roots table, so we report:
  - overall accuracy (all methods)
  - rule-only accuracy (excluding grammar_form fallbacks): the genuinely
    independent number
  - fallback rate

Sets:
  A: grammar_index.json forms (1,282, all confirmed in root 'forms' fields)
  B: zewadla forms confirmed in root 'forms' fields (379; 363 uncertain keys
     excluded: 198 pattern-code-suffixed artifacts, 4 bare pattern-code keys,
     161 keys of uncertain provenance)
  C: frequent AGE corpus types that also appear in A or B (natural + attested)
"""
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.stemmer import GeezStemmer
from src.normalizer import normalize_geez
from src.decomposer import get_consonant_skeleton

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
AGE_TRAIN = os.environ.get(
    "AGE_TRAIN_TSV", "/home/hatch/workspace/thesis-data/age/age_train.tsv")


def skel(s):
    if not s:
        return None
    return get_consonant_skeleton(normalize_geez(s))


def load_sets():
    d1 = json.load(open(os.path.join(BASE, "grammar_index.json"), encoding="utf-8"))
    d2 = json.load(open(os.path.join(BASE, "grammar_zewadla_index.json"), encoding="utf-8"))
    ftr1 = d1["form_to_roots"]
    ftr2 = d2["form_to_roots"]
    forms2 = set()
    for r in d2["roots"]:
        forms2.update(r.get("forms", []))
    codes = {"ቀተ", "ቀደ", "ተን", "ክህ", "ማህ", "ሴሰ", "ባረ", "ጦመ"}
    ftr2_clean = {k: v for k, v in ftr2.items() if k in forms2 and k not in codes}
    excluded = len(ftr2) - len(ftr2_clean)
    return ftr1, ftr2_clean, excluded


def corpus_types(top_n=5000):
    cnt = Counter()
    with open(AGE_TRAIN, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            geez = line.split("\t")[0]
            for tok in geez.split():
                t = tok.strip("።፣፤፥፦፧፨፡?!.,;:\"()[]")
                if t and re.fullmatch(r"[\u1200-\u135F]+", t):
                    cnt[t] += 1
    return cnt


def evaluate(stemmer, items, alt_attested=None):
    """items: list of (form, attested_roots, tag). Returns list of result dicts.
    alt_attested: optional dict form -> [roots] from a second source. When the
    two grammar sources disagree on lemmatization (e.g. Zewadla lists a derived
    form as headword while grammar_index maps it to the base root), a prediction
    matching either source counts as a hit."""
    out = []
    for form, attested, tag in items:
        try:
            res = stemmer.extract_root(form)
        except Exception as e:  # never let one form kill the battery
            out.append({"form": form, "attested": attested, "tag": tag,
                        "predicted": None, "method": "exception",
                        "confidence": 0.0, "word_class": None,
                        "match": False, "error": str(e)[:100]})
            continue
        pred = res.get("root")
        analysis = res.get("analysis", {}) or {}
        method = analysis.get("method")
        att_skel = {skel(a) for a in attested}
        if alt_attested and form in alt_attested:
            att_skel |= {skel(a) for a in alt_attested[form]}
        att_skel.discard(None)
        m = skel(pred) in att_skel if pred else False
        out.append({"form": form, "attested": attested, "tag": tag,
                    "predicted": pred, "method": method,
                    "confidence": res.get("confidence"),
                    "word_class": res.get("word_class"),
                    "match": m})
    return out


def summarize(results):
    n = len(results)
    hits = sum(1 for r in results if r["match"])
    rule = [r for r in results if r["method"] != "grammar_form"]
    rule_hits = sum(1 for r in rule if r["match"])
    fb = n - len(rule)
    fb_hits = hits - rule_hits
    return {
        "n": n,
        "accuracy": hits / n if n else 0.0,
        "hits": hits,
        "rule_n": len(rule),
        "rule_accuracy": rule_hits / len(rule) if rule else 0.0,
        "rule_hits": rule_hits,
        "fallback_n": fb,
        "fallback_rate": fb / n if n else 0.0,
        "fallback_hits": fb_hits,
    }


def main():
    ftr1, ftr2_clean, excluded = load_sets()
    print(f"Set A (grammar_index): {len(ftr1)} forms")
    print(f"Set B (zewadla, cleaned): {len(ftr2_clean)} forms ({excluded} uncertain excluded)")

    set_c = []
    if os.path.exists(AGE_TRAIN):
        cnt = corpus_types()
        book = set(ftr1) | set(ftr2_clean)
        for w, c in cnt.most_common():
            if w in book:
                att = list(dict.fromkeys(ftr1.get(w, []) + ftr2_clean.get(w, [])))
                set_c.append((w, att, f"freq={c}"))
        print(f"Set C (corpus types with book attestation): {len(set_c)} types, "
              f"{sum(cnt[w] for w, _, _ in set_c)} tokens")
    else:
        print(f"Set C skipped: corpus file not found at {AGE_TRAIN} "
              f"(set AGE_TRAIN_TSV to enable)")

    stemmer = GeezStemmer()

    items_a = [(f, v, "A") for f, v in ftr1.items()]
    items_b = [(f, v, "B") for f, v in ftr2_clean.items()]
    items_c = [(f, v, t) for f, v, t in set_c]

    res_a = evaluate(stemmer, items_a)
    print("Set A done")
    # Set B: accept either source when they disagree on lemmatization.
    # Zewadla lists some derived forms as headwords; grammar_index maps the
    # same forms to base roots. The analyzer follows the base-root analysis.
    res_b = evaluate(stemmer, items_b, alt_attested=ftr1)
    print("Set B done")
    res_c = evaluate(stemmer, items_c) if items_c else []
    print("Set C done" if items_c else "Set C skipped")

    all_res = res_a + res_b + res_c
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "source_attested_results.json")
    json.dump({"A": res_a, "B": res_b, "C": res_c,
               "excluded_zewadla": excluded},
              open(out_path, "w", encoding="utf-8"), ensure_ascii=False)
    print("wrote", out_path)

    for name, res in [("A", res_a), ("B", res_b), ("C", res_c)]:
        s = summarize(res)
        print(f"--- Set {name}: n={s['n']} "
              f"overall={s['hits']}/{s['n']}={s['accuracy']:.3f} "
              f"rule-only={s['rule_hits']}/{s['rule_n']}={s['rule_accuracy']:.3f} "
              f"fallback_rate={s['fallback_rate']:.3f} "
              f"(fallback hits {s['fallback_hits']}/{s['fallback_n']})")

    # word-class distribution of misses on A (diagnostic)
    from collections import Counter as C
    miss_wc = C(r["word_class"] for r in res_a if not r["match"])
    print("Set A miss word_classes:", dict(miss_wc.most_common(8)))
    meth = C(r["method"] for r in all_res)
    print("method distribution (all):", dict(meth.most_common(12)))


if __name__ == "__main__":
    main()
