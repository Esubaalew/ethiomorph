import sys
import os
import unittest

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.stemmer import GeezStemmer
from src.normalizer import normalize_geez

class TestGeezRootAnalyzer(unittest.TestCase):
    def setUp(self):
        self.stemmer = GeezStemmer()

    def test_logic_flow_samples(self):
        test_cases = [
            # (Input, Expected Root)
            ("ሐውጸነ", "ሀወጸ"), # Normalized: ሀወጸ
            ("መዝሙር", "ዘመረ"), # Corrected expectation
                               # ዝ -> ዘ. ሙ -> መ. ር -> ረ. So ዘመሰ?
                               # Actually 'r' is 're' (6th). 'z' is 'ze' (6th).
                               # So skeleton is ዘመሰ.
                               # But 'song' root is Z-M-R (ዘመረ).
                               # Let's check my decomposer logic.
                               # ረ (1st) -> ረ. ር (6th) -> ረ.
                               # So ዝሙር -> ዘመረ. Correct.
            ("ይቀተሉ", "ቀተለ"),
            ("ፀሐይ", "ጸሀየ"),
            ("አግብርተ", "ገበረ"),
        ]
        
        print("\n--- Testing Logic Flow Samples ---")
        for word, expected_root in test_cases:
            root, info, affixes = self.stemmer.extract_root(word)
            print(f"Word: {word} -> Root: {root} (Affixes: {affixes})")
            
            # Allow for some normalization differences in expectation (e.g. ሐ vs ሀ)
            # The stemmer normalizes everything.
            # So expected root should also be normalized.
            normalized_expected = normalize_geez(expected_root)
            self.assertEqual(root, normalized_expected, f"Failed for {word}")

    def test_high_expectation_cases(self):
        print("\n--- Testing High Expectation Cases ---")
        
        # 1. መስተጋብር -> ገበረ
        # መስተ (prefix) -> ጋብር.
        # ጋ (4th) -> ገ. ብ (6th) -> በ. ር (6th) -> ረ.
        # Root: ገበረ.
        word = "መስተጋብር"
        root, _, _ = self.stemmer.extract_root(word)
        print(f"Word: {word} -> Root: {root}")
        self.assertEqual(root, "ገበረ")
        
        # 2. ቆመ -> ቀወመ (Weak Root)
        word = "ቆመ"
        root, _, _ = self.stemmer.extract_root(word)
        print(f"Word: {word} -> Root: {root}")
        self.assertEqual(root, "ቀወመ")

        # 3. ሄደ -> ሀየደ (Weak Root - Extra test)
        word = "ሄደ"
        root, _, _ = self.stemmer.extract_root(word)
        print(f"Word: {word} -> Root: {root}")
        self.assertEqual(root, "ሀየደ")

if __name__ == '__main__':
    unittest.main()
