import sys
import os
import unittest

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.stemmer import GeezStemmer
from src.normalizer import normalize_geez
from src.decomposer import (
    devowelize,
    get_char_order,
    get_consonant_skeleton,
    AMBIGUOUS_VOWELS,
    AMBIGUOUS_VOWEL_DEFAULTS,
)

class TestAdvancedGeezRootAnalyzer(unittest.TestCase):
    def setUp(self):
        self.stemmer = GeezStemmer()

    def check_root(self, word, expected_root, description):
        result = self.stemmer.extract_root(word)
        root = result['root']
        # Normalize expectation just in case
        normalized_expected = normalize_geez(expected_root)
        print(f"[{description}] Word: {word} -> Got: {root}, Expected: {normalized_expected}")
        self.assertEqual(root, normalized_expected, f"Failed for {word} ({description})")

    def test_hollow_verbs(self):
        print("\n--- Testing Hollow Verbs ---")
        self.check_root("ቆመ", "ቀወመ", "Middle W hidden")
        self.check_root("ጌሠ", "ገየሰ", "Middle Y hidden (Giesa)")
        self.check_root("ቤተ", "በየተ", "Middle Y hidden (Beta)")

    def test_prefix_lookalikes(self):
        print("\n--- Testing Prefix Look-Alikes ---")
        self.check_root("መሐረ", "መሀረ", "Root starts with Ma")
        self.check_root("ተለወ", "ተለወ", "Root starts with Te")
        self.check_root("አመረ", "አመረ", "Root starts with A")

    def test_quadriliterals(self):
        print("\n--- Testing Quadriliterals ---")
        self.check_root("መነገነ", "መነገነ", "Quadriliteral starting with Ma")
        self.check_root("ደንግጸ", "ደነገጸ", "Quadriliteral standard")

    def test_complex_cases(self):
        print("\n--- Testing Complex Cases ---")
        self.check_root("ቀተልከኒ", "ቀተለ", "Double Suffix Strip")
        self.check_root("ኄር", "ሀየረ", "Normalization + Weak Root")
        
    def test_boss_level(self):
        print("\n--- Testing Boss Level (1-char) ---")
        self.check_root("ፃ", "ወፀአ", "1-char Tsa")
        self.check_root("ሖ", "ሐወረ", "1-char Ho")

    def test_ambiguous_tsi_unicode_default(self):
        print("\n--- Testing Ambiguous ጺ (S'ädai / Ts'äppai collision) ---")
        self.assertEqual(AMBIGUOUS_VOWELS["ጺ"], ("ጸ", "ፀ"))
        self.assertEqual(AMBIGUOUS_VOWEL_DEFAULTS["ጺ"], "ጸ")
        self.assertEqual(devowelize("ጺ"), "ጸ")
        self.assertEqual(get_char_order("ጺ"), 3)
        self.assertEqual(get_consonant_skeleton("ጺ"), "ጸ")

    def test_ambiguous_tsi_stemmer_does_not_bleed_to_tsa_row(self):
        print("\n--- Testing ጺ in stemmer analysis ---")
        result = self.stemmer.extract_root("ደንግጺ")
        self.assertNotIn("error", result)
        self.assertEqual(result["root"], normalize_geez("ደነገጸ"))
        self.assertIn("ጸ", result["root_consonants"])
        self.assertNotIn("ፀ", result["root_consonants"])

if __name__ == '__main__':
    unittest.main()
