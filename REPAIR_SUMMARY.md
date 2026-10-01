# EthioMorph Repair Summary

**Date:** 2026-09-30 (updated 2026-10-01)
**Status:** All four audit defects fixed. 41/41 tests pass (26 pre-existing + 15 new).

## Bug 1: Zewadla pattern-code labels misanalyzed

**Problem:** ሰርሐቀተ was parsed as root=ሰርሀቀ, pattern=derived_noun, suffix=[ተ].
The analyzer stripped ተ as a feminine/nominal ending before recognizing that
ቀተ is a Zewadla dictionary pattern code.

**Root cause:** The codebase already knew these were dictionary metadata
(grammar_loader.py: "Never strip these from surface forms"), but the
pattern-code check only existed in grammar index ingestion, not in analysis.
`strip_affixes` peeled ተ first.

**Fix (src/stemmer.py):**
- New `_match_pattern_code_label` method: matches word-final pattern codes
  from PATTERN_CODE_MAP, requiring the base to be a lexicon root or valid
  verbal citation shape (guards against false positives).
- Check inserted in `extract_root` before `strip_affixes`.
- New `pattern_override` parameter on `_build_result` so the code's pattern
  (e.g. perfective) is used directly instead of re-inferred.

**Result:** ሰርሐቀተ -> root=ሰርሐ, pattern=perfective, suffix=[ቀተ], method=pattern_code.
Paradigm head ቀተለ unaffected. Natural verbs unaffected.

## Bug 2a: Dead bihla contract value

**Problem:** stemmer.py checked `restored.get("by") == "bihla_from_dropped_c2"`,
but `restore_citation_root` never emitted that value for 2-letter stems.

**Fix (src/classical_rules.py):** Added the 2-letter bihla-drop case to
`restore_citation_root`: n==2 and C1 in 6th order restores C2 as ህ at sadis
(e.g. ብሉ -> ብህለ), emitting `"by": "bihla_from_dropped_c2"`. This makes the
stemmer's existing check live. Placed after the hollow_w/hollow_y cases
(disjoint: those need C1 in 7th, 3rd, or 5th order).

**Result:** The contract is now consistent. ይብሉ/ይብል -> ብህለ still passes.

## Bug 2b: Dead skeleton_fallback contract value

**Problem:** stemmer.py checked `restored["by"] in {"skeleton_fallback", "empty"}`,
but `restore_citation_root` never emits "skeleton_fallback".

**Fix (src/stemmer.py):** Reduced the check to `{"empty"}`, the only weak
restoration value actually emitted. Updated the comment accordingly.

## Bug 4: Punctuation accepted as roots

**Problem:** extract_root("።") returned "።" as a root. Punctuation supplied
7,941 supervised occurrences (6.82%) in the old label cache.

**Fix (src/stemmer.py):** At the start of `extract_root`, after normalization,
reject any input with no Ethiopic syllable letters (U+1200-U+135F; the
U+1360-U+137F range is punctuation/numerals). Returns root=None,
word_class="non_lexical", confidence=1.0.

**Result:** ። ፤ ፥ ፣ ፦ ፧, digits, and Latin all rejected. Single-char
imperative map (ፃ -> ወፀአ) unaffected.

## Test results

- 26 pre-existing tests: all pass (no regressions).
- 15 new tests (10 in tests/test_audit_fixes.py, 5 in tests/test_lexicon_grounded.py): all pass.
- Total: 41/41 OK.

## Files changed

- src/stemmer.py: pattern-code label support, non-lexical rejection,
  skeleton_fallback cleanup, pattern_override parameter, base_root
  annotation support for derived stems.
- src/classical_rules.py: 2-letter bihla-drop case in restore_citation_root.
- src/conjugator.py: stems.json missing-file handling, prefix-stripping
  safeguards for lexicon-typed roots.
- tests/test_audit_fixes.py: new, 10 regression tests.
- tests/test_lexicon_grounded.py: new, 5 consistency tests.
- scripts/curate_lexicon.py: new, lexicon curation (stem-as-root fix).
- scripts/merge_grammar_roots.py: new, grammar-index merge.
- scripts/validate_source_attested.py: new, source-attested validation.
- scripts/assign_unknown_types.py: new, type assignment.
- data/lexicon.json: curated (3,846 roots; 81 stems removed, 115 annotated
  with base_root, 23 artifacts removed, 284 type_a reviewed, 17 new roots).

## Not changed

- No em dashes added (pre-existing ones in comments left alone).
- Templates and grammar data files untouched.
- Public API of extract_root unchanged for valid words.
