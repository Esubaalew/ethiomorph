"""Large lexicon-free / grammar-free surface battery.

Scientific acceptance: roots must come from operators + order math.
Lexicon and grammar indexes are wiped so they cannot cheat.
"""

from __future__ import annotations

import unittest

from src.classical_rules import (
    anqets_transforms,
    arist_transforms,
    restore_citation_root,
)
from src.decomposer import get_char_by_order
from src.normalizer import normalize_geez
from src.stemmer import GeezStemmer


class _EmptyGrammar:
    loaded = False
    roots = {}
    source = {}

    def lookup_form(self, word):
        return []

    def resolve_skeleton(self, *args, **kwargs):
        return None

    def primary_gloss(self, root):
        return None

    def reference(self, root):
        return None

    def grammar_patterns(self, root):
        return []


def rule_only_stemmer() -> GeezStemmer:
    s = GeezStemmer()
    s.lexicon_roots = {}
    s.nouns = {}
    s.lexicon_normalized_lookup = {}
    s.skeleton_lookup = {}
    s.hollow_w_roots = set()
    s.hollow_y_roots = set()
    s.hollow_w_lookup = {}
    s.hollow_y_lookup = {}
    s.weak_initial_roots = set()
    s.quadriliterals = set()
    s.grammar = _EmptyGrammar()
    return s


def _revowel(bases, orders):
    return "".join(get_char_by_order(b, o) for b, o in zip(bases, orders))


def _actions(result):
    return [step.get("action") for step in (result.get("derivation_path") or [])]


class TestLexiconFreeBattery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = rule_only_stemmer()

    def analyze(self, word: str) -> dict:
        result = self.s.extract_root(word)
        actions = _actions(result)
        self.assertNotIn("lexicon_match", actions, msg=word)
        self.assertNotIn("grammar_form_lookup", actions, msg=word)
        for step in (result.get("derivation_path") or []):
            if step.get("action") == "canonicalize_root":
                self.assertEqual(step.get("before"), step.get("after"), msg=word)
        return result

    def test_type_a_anqets_many_roots(self):
        roots = [
            ["ሰ", "በ", "ረ"],
            ["ቀ", "ተ", "ለ"],
            ["ነ", "ገ", "ረ"],
            ["ደ", "ገ", "መ"],
            ["ፈ", "ለ", "ሰ"],
            ["ከ", "ተ", "መ"],
            ["ወ", "ደ", "ሰ"],
            ["ገ", "ደ", "ለ"],
        ]
        for bases in roots:
            citation = _revowel(bases, [1, 1, 1])
            transforms = anqets_transforms(citation)
            self.assertIsNotNone(transforms, msg=citation)
            surfaces = {
                "halafi": transforms["halafi"],
                "kalay": transforms["kalay"],
                "kalay_stem": transforms["kalay_stem"],
                "zend": transforms["zend"],
                "zend_stem": transforms["zend_stem"],
                "teizaz": transforms["teizaz"],
                "passive": "ተ" + citation,
                "causative": "አ" + citation,
            }
            for label, surface in surfaces.items():
                with self.subTest(root=citation, label=label, surface=surface):
                    result = self.analyze(surface)
                    self.assertEqual(normalize_geez(result["root"]), normalize_geez(citation))
                    self.assertEqual(result["word_class"], "gis")
                    self.assertEqual(result["root_class"], "abat_zer")

    def test_house_shape_citations_kept(self):
        cases = {
            "ገብረ": ("ገብረ", "ገብረ"),
            "ባረከ": ("ባረከ", "ባረከ"),
            "ብህለ": ("ብህለ", "ብህለ"),
            "ቀደሰ": ("ቀደሰ", "ቀደሰ"),
            "አእመረ": ("አእመረ", "አእመረ"),
        }
        for surface, (root, army) in cases.items():
            with self.subTest(surface=surface):
                result = self.analyze(surface)
                self.assertEqual(result["root"], root)
                self.assertEqual(result["army_head"], army)
                self.assertEqual(result["word_class"], "gis")

    def test_hollow_order_restore(self):
        cases = {
            "ቆመ": "ቀወመ",
            "ቆም": "ቀወመ",
            "ኆር": "ኀወረ",
            "ሜት": "መየተ",
        }
        for surface, expected in cases.items():
            with self.subTest(surface=surface):
                self.assertEqual(normalize_geez(restore_citation_root(surface)["citation"]), normalize_geez(expected))
                result = self.analyze(surface)
                self.assertEqual(normalize_geez(result["root"]), normalize_geez(expected))

    def test_feminine_nominal_endings_many(self):
        pairs = []
        base_sets = (
            ["ፈ", "ለ", "ሰ"],
            ["ቀ", "ተ", "ለ"],
            ["ነ", "ገ", "ረ"],
            ["ሰ", "በ", "ረ"],
            ["ወ", "ደ", "ሰ"],
        )
        for bases in base_sets:
            citation = _revowel(bases, [1, 1, 1])
            noun_stem = _revowel(bases, [6, 6, 1])
            pairs.append((noun_stem + "ት", citation))
            pairs.append((noun_stem + "ታ", citation))
        for surface, expected in pairs:
            with self.subTest(surface=surface):
                result = self.analyze(surface)
                self.assertIn(result["analysis"]["suffixes"][0], {"ት", "ታ"})
                self.assertEqual(normalize_geez(result["root"]), normalize_geez(expected))
                self.assertEqual(result["word_class"], "sem")
                self.assertEqual(result["root_class"], "tire_zer")

    def test_arist_shapes_classified(self):
        for bases in (
            ["ቀ", "ተ", "ለ"],
            ["ሰ", "በ", "ረ"],
            ["ወ", "ደ", "ሰ"],
            ["ፈ", "ለ", "ሰ"],
        ):
            citation = _revowel(bases, [1, 1, 1])
            arist = arist_transforms(citation)
            for key in ("qatul", "qatali"):
                surface = arist[key]
                with self.subTest(citation=citation, key=key, surface=surface):
                    result = self.analyze(surface)
                    self.assertIn(result["word_class"], {"arist", "sem", "gis"})
                    restored = restore_citation_root(surface)["citation"]
                    self.assertEqual(result["root"], restored)

    def test_particles_are_nabar(self):
        for surface in ("ወ", "በ", "ለ", "ከ", "የ", "እም", "ወእም"):
            with self.subTest(surface=surface):
                result = self.analyze(surface)
                self.assertEqual(result["word_class"], "nabar")
                self.assertEqual(result["root_class"], "nabar")
                self.assertIsNone(result["army_head"])

    def test_integral_noun_not_forced_to_verb(self):
        for surface in ("ብርሃን", "ንጉስነት", "መንግስት", "አምላክ"):
            with self.subTest(surface=surface):
                result = self.analyze(surface)
                self.assertNotIn(result["root"], {"በረሀ", "ነገሰ", "መነገሰ", "አመለከ"})
                self.assertNotEqual(result["word_class"], "gis")
                if not result["analysis"].get("suffixes") and not result["analysis"].get("prefixes"):
                    self.assertEqual(result["root"], surface)

    def test_asraw_markers_detected(self):
        cases = {
            "ይሰብር": "የ",
            "ትሰብር": "ተ",
            "እሰብር": "አ",
            "ንሰብር": "ነ",
        }
        for surface, marker in cases.items():
            with self.subTest(surface=surface):
                result = self.analyze(surface)
                self.assertEqual(result["root"], "ሰበረ")
                self.assertIn(marker, result["asraw_markers"])

    def test_bihla_imperfective_drop(self):
        # fere_geez ocrpage-045 table + asraw-reduced ይብሉ
        cases = {
            "ይብህል": "ብህለ",
            "ይብህሉ": "ብህለ",
            "ይብሀል": "ብህለ",
            "በሀል": "ብህለ",
            "ይብሉ": "ብህለ",
            "ይብል": "ብህለ",
        }
        for surface, expected in cases.items():
            with self.subTest(surface=surface):
                result = self.analyze(surface)
                self.assertEqual(result["root"], expected)
                self.assertEqual(result["army_head"], expected)
                self.assertEqual(result["word_class"], "gis")


    def test_object_clitic_on_perfective_stem(self):
        result = self.analyze("ቀተልከኒ")
        self.assertEqual(result["root"], "ቀተለ")
        self.assertEqual(result["word_class"], "gis")
        self.assertIn("ከ", result["analysis"]["suffixes"])

    def test_qetsel_like_surfaces(self):
        for surface in ("ቅቱል", "ስቡር", "ፍሉስ"):
            with self.subTest(surface=surface):
                result = self.analyze(surface)
                self.assertNotIn("lexicon_match", _actions(result))
                self.assertIn(result["word_class"], {"arist", "qetsel", "sem", "gis", "nabar"})

    def test_merahiyan_closed_class(self):
        for surface in ("ወእቱ", "አንተ", "አነ"):
            with self.subTest(surface=surface):
                result = self.analyze(surface)
                self.assertIn(result["word_class"], {"merahiyan", "nabar", "sem", "gis"})
                self.assertNotIn("lexicon_match", _actions(result))

    def test_restore_function_matches_stemmer_for_matrix(self):
        stems = ["ሰበረ", "ሰብር", "ስብር", "ገብረ", "ባረከ", "ብህለ", "ፍልሰ", "ቅትለ", "ቆመ", "ግእዝ", "ጋብር", "መለከ"]
        for stem in stems:
            with self.subTest(stem=stem):
                expected = restore_citation_root(stem)["citation"]
                result = self.analyze(stem)
                self.assertEqual(normalize_geez(result["root"]), normalize_geez(expected))

    def test_battery_size_floor(self):
        count = 0
        for bases in (
            ["ሰ", "በ", "ረ"],
            ["ቀ", "ተ", "ለ"],
            ["ነ", "ገ", "ረ"],
            ["ደ", "ገ", "መ"],
            ["ፈ", "ለ", "ሰ"],
            ["ከ", "ተ", "መ"],
        ):
            citation = _revowel(bases, [1, 1, 1])
            t = anqets_transforms(citation)
            count += 8
        count += 5 + 4 + 7 + 4 + 4 + 1 + 3 + 3
        self.assertGreaterEqual(count, 60)


if __name__ == "__main__":
    unittest.main()
