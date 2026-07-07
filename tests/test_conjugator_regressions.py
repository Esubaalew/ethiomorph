import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.conjugator import EthioMorphGenerator
from src.decomposer import devowelize, AMBIGUOUS_VOWELS


class TestPrefixPreservation(unittest.TestCase):
    def setUp(self):
        self.generator = EthioMorphGenerator()

    def _word(self, root, tense, subject="3sm", verb_type=None):
        result = self.generator.generate_word(root, tense, subject, verb_type=verb_type)
        self.assertNotIn("error", result, msg=str(result))
        return result["word"]

    def test_tanbala_perfective_identity(self):
        self.assertEqual(self._word("ተንበለ", "perfective"), "ተንበለ")

    def test_tanbala_jussive_not_double_marked(self):
        word = self._word("ተንበለ", "jussive")
        self.assertEqual(word, "ይተንብል")
        self.assertNotEqual(word, "ይተነብል")

    def test_type_a_prefix_lookalike_perfective(self):
        self.assertEqual(self._word("አመረ", "perfective"), "አመረ")

    def test_tagedele_reciprocal_perfective(self):
        result = self.generator.generate_word("ተጋደለ", "perfective", "3sm")
        self.assertNotIn("error", result)
        self.assertEqual(result["derivation"]["verb_type"], "type_a_reciprocal")
        self.assertEqual(result["word"], "ተጋደለ")

    def test_tagedele_reciprocal_perfective_3sf(self):
        self.assertEqual(self._word("ተጋደለ", "perfective", "3sf"), "ተጋደለት")

    def test_tagedele_reciprocal_imperfective(self):
        self.assertEqual(self._word("ተጋደለ", "imperfective"), "ይትጋደል")

    def test_tagedele_reciprocal_jussive(self):
        self.assertEqual(self._word("ተጋደለ", "jussive"), "ይትጋደል")


class TestTypeDPerfective(unittest.TestCase):
    def setUp(self):
        self.generator = EthioMorphGenerator()

    def _word(self, root):
        result = self.generator.generate_word(root, "perfective", "3sm")
        self.assertNotIn("error", result, msg=str(result))
        return result["word"]

    def test_kehle_perfective_identity(self):
        self.assertEqual(self._word("ክህለ"), "ክህለ")

    def test_lihqe_perfective_identity(self):
        self.assertEqual(self._word("ልህቀ"), "ልህቀ")

    def test_sehta_perfective_identity(self):
        self.assertEqual(self._word("ስሕተ"), "ስሕተ")

    def test_rihfe_perfective_identity(self):
        self.assertEqual(self._word("ርሕፀ"), "ርሕፀ")


class TestAmbiguousUnicode(unittest.TestCase):
    def test_tsi_ambiguity_documented(self):
        self.assertIn("ጺ", AMBIGUOUS_VOWELS)
        self.assertEqual(AMBIGUOUS_VOWELS["ጺ"], ("ጸ", "ፀ"))

    def test_tsi_devowelize_default(self):
        # Corpus default: S'ädai (ጸ) row, aligned with normalizer ፀ->ጸ mapping.
        self.assertEqual(devowelize("ጺ"), "ጸ")


class TestVerbTypeMatrix(unittest.TestCase):
    TENSES = ("perfective", "imperfective", "jussive", "imperative")
    OPTIONAL_TENSES = {
        "type_a_reciprocal": ("perfective", "imperfective", "jussive"),
    }

    SAMPLES = (
        ("ቀተለ", "type_a"),
        ("ቀደሰ", "type_b"),
        ("ክህለ", "type_d"),
        ("ጦመረ", "type_c_o"),
        ("ተንበለ", "type_tanbala"),
        ("አመረ", "type_a"),
        ("ተጋደለ", "type_a_reciprocal"),
    )

    def setUp(self):
        self.generator = EthioMorphGenerator()

    def test_verb_type_tense_matrix_smoke(self):
        for root, verb_type in self.SAMPLES:
            tenses = self.OPTIONAL_TENSES.get(verb_type, self.TENSES)
            for tense in tenses:
                subject = "2sm" if tense == "imperative" else "3sm"
                with self.subTest(root=root, verb_type=verb_type, tense=tense):
                    result = self.generator.generate_word(
                        root, tense, subject, verb_type=verb_type
                    )
                    self.assertNotIn("error", result, msg=str(result))
                    self.assertTrue(result.get("word"))


if __name__ == "__main__":
    unittest.main()
