"""Rule-first classical morphology tests (paper operators, not membership)."""

import unittest

from src.classical_rules import (
    ARMY_HEADS,
    SECONDARY_SOURCES,
    anqets_for_pattern,
    anqets_transforms,
    arist_transforms,
    army_head_sources,
    build_classical_analysis,
    classify_army_head,
    classify_word_class,
    detect_asraw_markers,
    match_anqets_surface,
    structural_features,
)
from src.stemmer import GeezStemmer


class TestClassicalRules(unittest.TestCase):
    def test_eight_army_head_templates_only(self):
        self.assertEqual(len(ARMY_HEADS), 8)
        for info in ARMY_HEADS.values():
            self.assertNotIn("members", info)

    def test_structural_features_qatala(self):
        feat = structural_features("\u1240\u1270\u1208")
        self.assertEqual(feat["skel_len"], 3)
        self.assertTrue(feat["ends_geez"])
        self.assertEqual(feat["c2_order"], 1)

    def test_army_by_shape_not_membership(self):
        # source_rule: fere_geez.ch4.army_heads.*
        self.assertEqual(classify_army_head("\u1240\u1270\u1208")["head"], "\u1240\u1270\u1208")
        self.assertEqual(classify_army_head("\u1240\u12f0\u1230")["head"], "\u1240\u12f0\u1230")
        self.assertEqual(classify_army_head("\u1308\u1265\u1228")["head"], "\u1308\u1265\u1228")
        self.assertEqual(classify_army_head("\u1263\u1228\u12a8")["head"], "\u1263\u1228\u12a8")
        self.assertEqual(classify_army_head("\u1224\u1218")["head"], "\u1224\u1218")
        self.assertEqual(classify_army_head("\u1265\u1205\u1208")["head"], "\u1265\u1205\u1208")
        self.assertEqual(classify_army_head("\u1246\u1218")["head"], "\u1246\u1218")
        self.assertEqual(classify_army_head("\u12a0\u12a5\u1218\u1228")["head"], "\u12a0\u12a5\u1218\u1228")

        # Strong triliteral C2=1st → ቀተለ shape (ነገረ)
        self.assertEqual(classify_army_head("\u1290\u1308\u1228")["head"], "\u1240\u1270\u1208")
        # Geminate C2=C3 → ቀደሰ shape (ሐተተ)
        self.assertEqual(classify_army_head("\u1210\u1270\u1270")["head"], "\u1240\u12f0\u1230")
        # C2 sadis → ገብረ shape (ሰርሐ)
        self.assertEqual(classify_army_head("\u1230\u122d\u1210")["head"], "\u1308\u1265\u1228")
        # Laryngeal middle → ብህለ house
        self.assertEqual(
            classify_army_head("\u1265\u1205\u1208")["head"], "\u1265\u1205\u1208"
        )
        # Hollow collapsed → ቆመ
        self.assertEqual(classify_army_head("\u1246\u1218")["head"], "\u1246\u1218")

    def test_asraw_markers_from_prefixes(self):
        markers = detect_asraw_markers(["\u12ed"], "\u1240\u1275\u120d")
        self.assertIn("\u12e8", markers)

    def test_anqets_transforms_qatala(self):
        # Fere Ge'ez / geezgram: ቀተለ → ይቀትል → ይቅትል → ቅትል
        t = anqets_transforms("\u1240\u1270\u1208")
        self.assertIsNotNone(t)
        self.assertEqual(t["halafi"], "\u1240\u1270\u1208")
        self.assertEqual(t["kalay"], "\u12ed\u1240\u1275\u120d")
        self.assertEqual(t["zend"], "\u12ed\u1245\u1275\u120d")
        self.assertEqual(t["teizaz"], "\u1245\u1275\u120d")
        matched = match_anqets_surface("\u12ed\u1240\u1275\u120d", "\u1240\u1270\u1208")
        self.assertEqual(matched["name"], "\u12ab\u120d\u12d3\u12ed")

    def test_arist_transforms(self):
        a = arist_transforms("\u1240\u1270\u1208")
        self.assertEqual(a["qatul"], "\u1245\u1271\u120d")
        self.assertEqual(a["qatali"], "\u1240\u1273\u120a")

    def test_word_class_routing(self):
        gis = classify_word_class(
            root="\u1240\u1270\u1208",
            stem="\u1240\u1270\u1208",
            prefixes=[],
            suffixes=[],
            pattern_name="perfective",
            method="lexicon",
            in_lexicon_verbs=True,
            in_nouns=False,
            noun_has_verbal_root=False,
        )
        self.assertEqual(gis["word_class"], "gis")

        nabar = classify_word_class(
            root="\u12c8",
            stem="\u12c8",
            prefixes=[],
            suffixes=[],
            pattern_name="particle_phrase",
            method="particle_phrase",
            in_lexicon_verbs=False,
            in_nouns=False,
            noun_has_verbal_root=False,
        )
        self.assertEqual(nabar["word_class"], "nabar")

        sem = classify_word_class(
            root="\u1218\u1208\u12a8",
            stem="\u12a0\u121d\u120b\u12ad",
            prefixes=[],
            suffixes=["\u1290"],
            pattern_name="derived_noun",
            method="lexicon_noun",
            in_lexicon_verbs=False,
            in_nouns=True,
            noun_has_verbal_root=True,
        )
        self.assertEqual(sem["word_class"], "sem")

    def test_anqets_halafi(self):
        info = anqets_for_pattern({"name": "perfective"})
        self.assertEqual(info["name"], "\u1283\u120b\u134a")

    def test_build_classical_analysis_qatala(self):
        classical = build_classical_analysis(
            root="\u1240\u1270\u1208",
            stem="\u1240\u1270\u1208",
            prefixes=[],
            pattern={"name": "perfective"},
            root_type="type_a",
            method="lexicon",
            in_lexicon_verbs=True,
        )
        self.assertEqual(classical["word_class"], "gis")
        self.assertEqual(classical["root_class"], "abat_zer")
        self.assertEqual(classical["army_head"], "\u1240\u1270\u1208")
        self.assertIsNotNone(classical["anqets_transforms"])
        self.assertIsNotNone(classical["structural_features"])

    def test_geezgram_qatala_table(self):
        stemmer = GeezStemmer()
        perfect = stemmer.extract_root("\u1240\u1270\u1208")
        self.assertEqual(perfect["army_head"], "\u1240\u1270\u1208")
        self.assertEqual(perfect["word_class"], "gis")
        self.assertEqual(perfect["anqets"]["name"], "\u1283\u120b\u134a")

        imperfect = stemmer.extract_root("\u12ed\u1240\u1275\u120d")
        self.assertEqual(imperfect["root_class"], "abat_zer")
        self.assertTrue(
            imperfect["asraw_markers"] or "\u12ed" in imperfect["analysis"]["prefixes"]
        )
        self.assertIn(
            SECONDARY_SOURCES["geezgram_vol2_army_heads"],
            army_head_sources("\u1240\u1270\u1208"),
        )

    def test_nabar_and_amlak_nonverb(self):
        stemmer = GeezStemmer()
        nabar = stemmer.extract_root("\u12c8")
        self.assertEqual(nabar["word_class"], "nabar")
        self.assertEqual(nabar["root_class"], "nabar")
        self.assertIsNone(nabar["army_head"])

        amlak = stemmer.extract_root("\u12a0\u121d\u120b\u12ad\u1290")
        self.assertEqual(amlak["word_class"], "sem")
        self.assertEqual(amlak["root_class"], "tire_zer")
        self.assertEqual(amlak["root"], "\u1218\u1208\u12a8")


    def test_filseta_feminine_ending_rule(self):
        # Rule path (not lexicon cheat): strip ታ, then 1st-order skeleton => citation.
        # source_rule: fere_geez.ch4.tire_zer.feminine_ending
        from src.decomposer import get_consonant_skeleton
        stemmer = GeezStemmer()
        result = stemmer.extract_root("ፍልሰታ")
        self.assertEqual(result["analysis"]["suffixes"], ["ታ"])
        self.assertEqual(result["root"], get_consonant_skeleton("ፍልሰ"))
        self.assertEqual(result["word_class"], "sem")
        self.assertEqual(result["root_class"], "tire_zer")
        self.assertEqual(result["analysis"]["pattern"]["name"], "derived_noun")


if __name__ == "__main__":
    unittest.main()
