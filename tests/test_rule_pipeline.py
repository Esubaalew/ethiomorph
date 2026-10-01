"""Universal rule-pipeline regressions (publishable acceptance battery).

Every case must be explainable by operators + order math.
Lexicon may supply gloss after the root is recovered; it must not be
the only reason the root is found.
"""

from __future__ import annotations

import unittest

from src.classical_rules import restore_citation_root
from src.decomposer import get_consonant_skeleton
from src.stemmer import GeezStemmer


class TestUniversalRulePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = GeezStemmer()

    def _root(self, word: str) -> str:
        return self.s.extract_root(word)["root"]

    def test_feminine_ending_operator_is_universal(self):
        # source_rule: fere_geez.ch4.tire_zer.feminine_ending
        cases = {
            "ፍልሰታ": "ፈለሰ",
            "ፍልሰት": "ፈለሰ",
            "ቅትለት": "ቀተለ",
        }
        for surface, expected in cases.items():
            with self.subTest(surface=surface):
                result = self.s.extract_root(surface)
                self.assertTrue(
                    set(result["analysis"]["suffixes"]) & {"ታ", "ት", "አት", "ተ"}
                )
                self.assertEqual(result["root"], expected)
                self.assertEqual(result["word_class"], "sem")
                self.assertEqual(result["root_class"], "tire_zer")
                stem = result["analysis"]["stem"]
                self.assertEqual(result["root"], restore_citation_root(stem)["citation"])

    def test_citation_restore_keeps_house_shapes(self):
        self.assertEqual(restore_citation_root("ገብረ")["citation"], "ገብረ")
        self.assertEqual(restore_citation_root("ባረከ")["citation"], "ባረከ")
        self.assertEqual(restore_citation_root("ብህለ")["citation"], "ብህለ")
        self.assertEqual(restore_citation_root("ቀተለ")["citation"], "ቀተለ")
        self.assertEqual(restore_citation_root("ፍልሰ")["citation"], "ፈለሰ")
        self.assertEqual(restore_citation_root("ቀትል")["citation"], "ቀተለ")
        self.assertEqual(restore_citation_root("ቅትል")["citation"], "ቀተለ")

    def test_anqets_surfaces_recover_qatala(self):
        for surface in (
            "ቀተለ",
            "ይቀትል",
            "ይቅትል",
            "ቅትል",
            "ተቀተለ",
        ):
            with self.subTest(surface=surface):
                result = self.s.extract_root(surface)
                self.assertEqual(result["root"], "ቀተለ")
                self.assertEqual(result["word_class"], "gis")

    def test_gabra_not_flattened_or_grammar_hijacked(self):
        result = self.s.extract_root("ገብረ")
        self.assertEqual(result["root"], "ገብረ")
        self.assertEqual(result["army_head"], "ገብረ")
        self.assertNotEqual(result["root"], "ቀተረ")
        # Blind skeleton would flatten C2 sadis away from gabra citation
        self.assertNotEqual(result["root"], get_consonant_skeleton("ገብረ"))

    def test_no_forced_verbal_root_for_integral_noun_shape(self):
        result = self.s.extract_root("ብርሃን")  # birhan
        self.assertEqual(result["analysis"]["suffixes"], [])
        self.assertEqual(result["root"], "ብርሃን")
        self.assertIn(result["root_class"], {"nabar", "tire_zer"})
        self.assertNotIn(result["root"], {"በርሀ", "በረሀ", "በረሀነ"})

    def test_hollow_restore_by_order(self):
        self.assertEqual(self._root("ቆመ"), "ቀወመ")
        self.assertEqual(self._root("ቆም"), "ቀወመ")

    def test_particle_nabar_never_invents_verb(self):
        result = self.s.extract_root("ወ")
        self.assertEqual(result["word_class"], "nabar")
        self.assertIsNone(result["army_head"])


if __name__ == "__main__":
    unittest.main()
