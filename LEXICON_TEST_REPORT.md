# geezRPA Validation Report: Lexicon-Grounded and Source-Attested Root Recovery

Date: 2026-09-30 (historical; pre-curation metrics)
Analyzer: repaired geezRPA (workspace copy; Mac repo updated 2026-10-01)

**Note:** This report documents the pre-curation validation state. The
lexicon has since been curated (see scripts/curate_lexicon.py and
REPAIR_SUMMARY.md for current state). Metrics below are historical.

## What this report covers

Two kinds of testing, which must not be confused:

1. **Consistency test** (conjugator round trip): generate forms with the
   repo's own conjugator, recover roots with the analyzer. This checks
   that the two components agree. It does NOT prove real-world accuracy,
   because both sides share the same lexicon and grammar resources.

2. **Source-attested validation** (independent): grammar-book forms mapped
   to roots by the books themselves (never conjugator output). The
   analyzer never sees the mapping; it must derive the root by analysis.

An earlier version of this report called the consistency test "not
circular" and declared the analyzer fit for label-cache generation. Both
claims were overstated and are withdrawn below.

## Root inventory enrichment (corrected)

Merged 2,032 roots from grammar_index.json and grammar_zewadla_index.json
into lexicon.json (backup: data/lexicon.json.pre_merge_20260930.bak).

Types were assigned from a pattern-code mapping inferred from overlapping
roots (ቀተ→type_a, ቀደ→type_b, ተን→type_tanbala, ክህ→type_d,
ማህ→type_mahräka, ሴሰ→type_c_e, ባረ→type_c, ጦመ→type_c_o).

Correction: **284 of the 2,032 new roots had no recognized pattern code
and were defaulted to type_a as a guess.** The earlier claim that "types
were not guessed" is false for these entries. A full review of the 284
is in type_a_review_284.json / type_a_review_284.tsv:

- Reassigned on phonological evidence: 234
  (227 quadriliteral, 4 hollow_w, 3 hollow_y)
- Genuinely unknown verb class: 27 (sound triliteral, no pattern
  evidence; must be marked unknown, not left as type_a)
- Extraction artifacts, not valid roots: 23 (pattern-code suffixes like
  ሄደቀተ = ሄደ+ቀተ; 17 duplicate existing lexicon entries and should be
  removed, 6 need manual review of the stripped form)

The merge also added derived stems as "root" entries (e.g. ተቀበለ alongside
its base root ቀበለ). This causes the systematic error described below and
must be curated before any label-cache generation.

## Consistency test (conjugator round trip)

For each lexicon root, generated 6 conjugated surface forms with the
repo's own conjugator, then ran the repaired extract_root on each form.
22,739 surface forms from 3,790 roots. Comparison on consonantal skeletons.

- Overall: 17,325/22,739 = 76.2%
- By type: type_a 78.2%, type_b 79.9%, type_c 83.6%, type_d 67.6%,
  hollow_w 100%, hollow_y 72.2%, weak_initial 75.0%, quadriliteral 66.7%

Interpretation: the analyzer and conjugator are consistent with each
other at 76.2%. This is a useful regression signal, not a measure of
real-world accuracy.

Note on the conjugator warning: test runs emitted
"Warning: Data files (templates, stems, or lexicon) not found." The
missing resource is data/stems.json (derived-stem definitions), which was
never shipped with the data directory. It does NOT affect the 76.2%
figure: generate_word (used by the test) never touches stems_data, and the
test passes verb_type explicitly. Fixed in the workspace copy
(src/conjugator.py): each data file now loads independently with a
specific warning, self.stems_data is initialized, and a missing stems.json
no longer blocks the conjugator lexicon from loading (it previously left
the conjugator lexicon empty) or crashes generate_stem with
AttributeError. The 76.2% figure was re-verified unchanged after the fix.

## Source-attested validation (independent)

Gold: form_to_roots from the two grammar-book indexes. Excluded 363
zewadla keys of uncertain provenance (198 pattern-code-suffixed
artifacts, 4 bare pattern-code keys, 161 keys not confirmed in any root's
forms field). The analyzer's grammar-form fallback path (which consults
the same table) fired 0 times across all 1,703 forms, so every result
below is independent rule/lexicon analysis.

- Set A (grammar_index, 1,282 book forms): **1088/1282 = 84.9%**
- Set B (zewadla, cleaned, 379 forms): **313/379 = 82.6%**
  (caveat: the zewadla index contains synonym-confusion artifacts,
  e.g. ገብረ mapped to ቀትረ/ንኡስ, which corrupt a small number of gold
  entries)
- Set C (frequent AGE corpus types with book attestation, 14 types from
  top-5000): **6/14 = 42.9%**; 2 misses are zewadla gold artifacts, the
  other 6 are the stem-as-root issue below

Miss analysis (Set A, 194 misses):
- 158 (12.3%) are **stem-as-root**: the form is a derived stem that the
  merge added to the lexicon as a headword (e.g. ተቀበለ, whose book-mapped
  base root is ቀበለ). The analyzer's direct lexicon-hit preference
  returns the stem verbatim instead of stripping to the base root.
- 36 are other failures (affix handling, spelling variants).

Coverage proxy (not accuracy): for the top-1,000 frequent AGE corpus
word types, 50.4% receive a predicted root that exists in the lexicon
inventory; the rest get rule-derived roots outside the inventory. The
label cache must decide how to treat out-of-inventory predictions.

## Two analyzer bugs found and fixed this session

1. **Weak-initial imperfective swallowed by the PDF bihla path.**
   `analyze_surface_pdf` claimed ይሃብ-type forms as bihla-house stems
   (→ ይህበ) before prefix stripping ran. Fix: `_try_weak_initial_imperfective`
   checks ይ/ት/እ + 2-char stem against known weak-initial roots first.
   (ይሃብ → ወሀበ now correct.)

2. **ወ radical stripped as conjunction prefix.**
   ይወርዱ → stripped ይ, then stripped ወ as "and" prefix → ርህደ.
   Fix: block stripping single ወ when 'ወ' + skeleton(remaining) is a
   known weak-initial root. (ይወርዱ → ወረደ now correct.)

Genuine bihla forms unaffected: ብህል → ብህለ, ይብል → ብህለ still correct.

## Regression

All 41 unit tests pass (36 existing + 5 new weak-initial tests).

## Verdict (corrected)

The analyzer is **not yet fit for label-cache generation**. What it has:
consistent 76.2% round-trip agreement, 84.9%/82.6% on book forms with
fully independent analysis paths, two real bugs fixed, and a reviewed
root inventory.

What must happen first:
1. Curate the merged lexicon: remove the 23 pattern-code artifacts,
   resolve the 27 unknown-type entries, and link derived-stem headwords
   (ተቀበለ-type) to their base roots so the analyzer stops returning
   stems as roots (the 12.3% systematic error).
2. Decide the out-of-inventory policy for the label cache (49.6% of
   frequent corpus types).
3. Re-run this validation after curation; the scientific label cache is
   regenerated only then.
