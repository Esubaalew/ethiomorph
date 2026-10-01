import sys
import os
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.stemmer import GeezStemmer
from src.normalizer import normalize_geez


class TestGeezRootAnalyzer(unittest.TestCase):
    def setUp(self):
        self.stemmer = GeezStemmer()

    def test_logic_flow_samples(self):
        test_cases = [
            ("\u1200\u12cd\u1338\u1290", "\u1200\u12c8\u1338"),
            ("\u1218\u12dd\u1219\u122d", "\u12d8\u1218\u1228"),
            ("\u12ed\u1240\u1270\u1209", "\u1240\u1270\u1208"),
            ("\u1338\u1210\u12ed", "\u1338\u1200\u12e8"),
            ("\u12a0\u130d\u1265\u122d\u1270", "\u1308\u1260\u1228"),
        ]

        print("\n--- Testing Logic Flow Samples ---")
        for word, expected_root in test_cases:
            result = self.stemmer.extract_root(word)
            root = result["root"]
            affixes = result["analysis"].get("prefixes", []) + result["analysis"].get("suffixes", [])
            print(f"Word: {word} -> Root: {root} (Affixes: {affixes})")
            self.assertEqual(
                normalize_geez(root),
                normalize_geez(expected_root),
                f"Failed for {word}",
            )

    def test_high_expectation_cases(self):
        print("\n--- Testing High Expectation Cases ---")

        word = "\u1218\u1235\u1270\u130b\u1265\u122d"
        root = self.stemmer.extract_root(word)["root"]
        print(f"Word: {word} -> Root: {root}")
        self.assertEqual(normalize_geez(root), normalize_geez("\u1308\u1265\u1228"))

        word = "\u1246\u1218"
        root = self.stemmer.extract_root(word)["root"]
        print(f"Word: {word} -> Root: {root}")
        self.assertEqual(normalize_geez(root), normalize_geez("\u1240\u12c8\u1218"))

        word = "\u1204\u12f0"
        root = self.stemmer.extract_root(word)["root"]
        print(f"Word: {word} -> Root: {root}")
        self.assertEqual(normalize_geez(root), normalize_geez("\u1200\u12e8\u12f0"))


if __name__ == '__main__':
    unittest.main()
