import sys
import os
import unittest

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.stemmer import GeezStemmer
from src.normalizer import normalize_geez

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

if __name__ == '__main__':
    unittest.main()
