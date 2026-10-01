"""Regression tests for the four EthioMorph audit fixes (2026-09-30).

1. Zewadla pattern-code labels: citation + pattern code (e.g. ሰርሐቀተ)
   must parse as root + pattern, not strip ተ as a feminine ending.
2. Contract values: restore_citation_root must emit "bihla_from_dropped_c2"
   for 2-letter C1=6th-order stems; stemmer must not check for values that
   are never emitted ("skeleton_fallback").
3. Punctuation and other non-lexical input must be rejected, not rooted.
"""
from __future__ import annotations

import unittest

from src.classical_rules import restore_citation_root
from src.stemmer import GeezStemmer


class TestPatternCodeLabels(unittest.TestCase):
    def setUp(self):
        self.stemmer = GeezStemmer()

    def analyze(self, word):
        return self.stemmer.extract_root(word)

    def test_serhake_te_label(self):
        # ሰርሐቀተ = ሰርሐ (root) + ቀተ (Zewadla perfective code).
        result = self.analyze("ሰርሐቀተ")
        self.assertEqual(result["root"], "ሰርሐ")
        self.assertEqual(result["analysis"]["pattern"]["name"], "perfective")
        self.assertEqual(result["analysis"]["suffixes"], ["ቀተ"])
        self.assertEqual(result["analysis"]["method"], "pattern_code")

    def test_paradigm_head_not_stripped(self):
        # ቀተለ is a paradigm head, not root + code.
        result = self.analyze("ቀተለ")
        self.assertEqual(result["root"], "ቀተለ")

    def test_natural_verb_unaffected(self):
        result = self.analyze("ወሰበረ")
        self.assertEqual(result["root"], "ሰበረ")
        self.assertEqual(result["analysis"]["pattern"]["name"], "perfective")

    def test_feminine_ending_still_strips(self):
        # ንግሥት ends in ት but not a pattern code; nominal path intact.
        result = self.analyze("ንግሥት")
        self.assertEqual(result["analysis"]["pattern"]["name"], "derived_noun")


class TestContractValues(unittest.TestCase):
    def test_bihla_from_dropped_c2_emitted(self):
        restored = restore_citation_root("ብሉ")
        self.assertEqual(restored["by"], "bihla_from_dropped_c2")
        self.assertEqual(restored["citation"], "ብህለ")

    def test_bihla_end_to_end(self):
        stemmer = GeezStemmer()
        for surface in ("ይብሉ", "ይብል"):
            with self.subTest(surface=surface):
                result = stemmer.extract_root(surface)
                self.assertEqual(result["root"], "ብህለ")

    def test_no_skeleton_fallback_reference(self):
        import inspect
        from src.stemmer import GeezStemmer as GS
        self.assertNotIn("skeleton_fallback", inspect.getsource(GS.extract_root))


class TestNonLexicalRejection(unittest.TestCase):
    def setUp(self):
        self.stemmer = GeezStemmer()

    def test_ethiopic_punctuation_rejected(self):
        for punct in ("።", "፤", "፥", "፣", "፦", "፧"):
            with self.subTest(punct=punct):
                result = self.stemmer.extract_root(punct)
                self.assertIsNone(result["root"])
                self.assertEqual(result["word_class"], "non_lexical")

    def test_digits_and_latin_rejected(self):
        for token in ("123", "hello"):
            with self.subTest(token=token):
                result = self.stemmer.extract_root(token)
                self.assertIsNone(result["root"])

    def test_single_char_imperative_still_works(self):
        # ፃ is an Ethiopic letter; the imperative map must still fire.
        result = self.stemmer.extract_root("ፃ")
        self.assertIsNotNone(result["root"])


class TestWeakInitialImperfective(unittest.TestCase):
    """Weak-initial (ወ) verbs in the imperfective/jussive.

    The PDF bihla path must not claim ይ/ት-prefixed forms of weak-initial
    verbs as bihla-house stems, and the ወ conjunction prefix must not be
    stripped when it is the root's first radical.
    """

    def setUp(self):
        self.stemmer = GeezStemmer()

    def test_yi_prefix_weak_initial(self):
        result = self.stemmer.extract_root("ይሃብ")
        self.assertEqual(result["root"], "ወሀበ")

    def test_ti_prefix_weak_initial(self):
        result = self.stemmer.extract_root("ትሀብ")
        self.assertEqual(result["root"], "ወሀበ")

    def test_waw_radical_not_stripped(self):
        # ይወርዱ: strip ይ, keep ወ (it is the root radical, not a prefix).
        result = self.stemmer.extract_root("ይወርዱ")
        self.assertEqual(result["root"], "ወረደ")

    def test_bihla_stems_unaffected(self):
        # Genuine bihla-house forms must still take the PDF path.
        self.assertEqual(self.stemmer.extract_root("ብህል")["root"], "ብህለ")
        self.assertEqual(self.stemmer.extract_root("ይብል")["root"], "ብህለ")

    def test_strong_verb_unaffected(self):
        self.assertEqual(self.stemmer.extract_root("ይሰብር")["root"], "ሰበረ")


if __name__ == "__main__":
    unittest.main()
