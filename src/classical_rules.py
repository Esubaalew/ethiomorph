"""Classical Ge'ez morphology: rule operators, not word catalogs.

Sources: Fere Ge'ez, geezgram 1–4, gzamargna ርባሐ ስም ወአንቀጽ.

Hardcoded only as scientific constants:
  - eight ሠራዊት አለቆች template names
  - አሥራው ቀለማት ተ/አ/የ/ነ
  - አንቀጽ inventory + ዐቢይ/ንዑስ/ደቂቅ ranks
  - finite መራሕያን / ባለቤት / particle operator sets

Army membership lists are intentionally absent; heads are shape templates.
"""

from __future__ import annotations

from src.decomposer import (
    LARYNGEALS,
    WEAK_CONSONANTS,
    detect_verb_home,
    devowelize,
    get_char_by_order,
    get_char_order,
    get_consonant_skeleton,
)
from src.normalizer import normalize_geez

SECONDARY_SOURCES = {
    "geezgram_vol2_army_heads": "geezgram.vol2.erba_gis.army_heads",
    "geezgram_vol2_qatala_table": "geezgram.vol2.erba_gis.qatala",
    "gzamargna_rbaha": "gzamargna.rbaha_sem_weanqets",
}

# Template names only (musts). No member armies.
ARMY_HEADS: dict[str, dict] = {
    "\u1240\u1270\u1208": {
        "geez_name": "\u1240\u1270\u1208",
        "english_name": "Qatala paradigm",
        "source_rule": "fere_geez.ch4.army_heads.qatala",
    },
    "\u1240\u12f0\u1230": {
        "geez_name": "\u1240\u12f0\u1230",
        "english_name": "Qaddasa paradigm",
        "source_rule": "fere_geez.ch4.army_heads.qaddasa",
    },
    "\u1308\u1265\u1228": {
        "geez_name": "\u1308\u1265\u1228",
        "english_name": "Gabra paradigm",
        "source_rule": "fere_geez.ch4.army_heads.gabra",
    },
    "\u12a0\u12a5\u1218\u1228": {
        "geez_name": "\u12a0\u12a5\u1218\u1228",
        "english_name": "Amara paradigm",
        "source_rule": "fere_geez.ch4.army_heads.amara",
    },
    "\u1263\u1228\u12a8": {
        "geez_name": "\u1263\u1228\u12a8",
        "english_name": "Baraka paradigm",
        "source_rule": "fere_geez.ch4.army_heads.baraka",
    },
    "\u1224\u1218": {
        "geez_name": "\u1224\u1218",
        "english_name": "Sema paradigm",
        "source_rule": "fere_geez.ch4.army_heads.sema",
    },
    "\u1265\u1205\u1208": {
        "geez_name": "\u1265\u1205\u1208",
        "english_name": "Bihla paradigm",
        "source_rule": "fere_geez.ch4.army_heads.bihla",
    },
    "\u1246\u1218": {
        "geez_name": "\u1246\u1218",
        "english_name": "Qoma paradigm",
        "source_rule": "fere_geez.ch4.army_heads.qoma",
    },
}

ASRAW_QELAMAT = ("\u1270", "\u12a0", "\u12e8", "\u1290")

# Object / person clitics: only strip when a verbal prefix is present,
# or when the residue is clearly a non-citation conjugated stem.
# Bare letters that also occur as radicals (ከ/ነ/…) must not peel citations.
CONTEXT_SENSITIVE_SUFFIXES = frozenset({
    "ን", "ም", "ክ",
    "ከ", "ኪ", "ኩ",
    "ነ", "ኒ", "ና",
    "ኡ", "ኣ",
    "ሙ", "ማ",
    "ዎ", "ዮ", "ዩ",
    "ክሙ", "ክን", "ኦሙ", "ኦን", "ዎሙ", "ዎን",
})

# Feminine / derived-noun endings (same radical ተ family at different orders).
# ት (6th) and ታ (4th) are operators, not extra root consonants.
# source_rule: fere_geez.ch4.tire_zer.feminine_ending
NOMINAL_FEMININE_ENDINGS = frozenset({
    "\u1273",  # ታ
    "\u1275",  # ት
    "\u12a0\u1275",  # አት
    "\u1270",  # ተ
})


# Finite ባለቤት / possessive operators (Fere Ge'ez paradigm endings).
BALABET_SUFFIXES = frozenset({
    "\u1201", "\u1206\u1219", "\u1203", "\u1206\u1295",
    "\u12a8", "\u12ad\u1219", "\u12aa", "\u12ad\u1295",
    "\u12e8", "\u1290", "\u12cd", "\u12ce\u1219", "\u12cb", "\u12ce\u1295",
    "\u1293", "\u1295",
})

# Finite መራሕያን (person operators). Closed class by definition.
MERAHIYAN_FORMS = frozenset({
    "\u12cd\u12a5\u1271", "\u12cd\u12a5\u1276\u1219", "\u12ed\u12a5\u1272", "\u12cd\u12a5\u1276\u1295",
    "\u12a0\u1295\u1270", "\u12a0\u1295\u1275\u1219", "\u12a0\u1295\u1272", "\u12a0\u1295\u1275\u1295",
    "\u12a0\u1290", "\u1295\u1205\u1290", "\u12a5\u1218\u1295\u1271",
})

# Citation nouns that are not verb roots. Glosses are not invented here.
# The lexicon noun list is only six derived nouns; these stay out of pdf_anqets.
CITATION_NOUNS = frozenset({
    "\u1230\u121b\u12ed",  # ሰማይ
    "\u121d\u12f5\u122d",  # ምድር
    "\u1264\u1275",  # ቤት
    "\u130d\u12a5\u12dd",  # ግእዝ
    "\u1290\u134d\u1235",  # ነፍስ
})

ANQETS_BY_PATTERN = {
    "perfective": {
        "name": "\u1283\u120b\u134a",
        "geez_name": "\u1283\u120b\u134a / \u1240\u12f3\u121b\u12ed \u12a0\u1295\u1240\u133d",
        "rank": "\u12d0\u1262\u12ed",
        "source_rule": "fere_geez.ch4.anqets.halafi",
    },
    "imperfective": {
        "name": "\u12ab\u120d\u12d3\u12ed",
        "geez_name": "\u12ab\u120d\u12d3\u12ed / \u1275\u1295\u1262\u1275 \u12a0\u1295\u1240\u133d",
        "rank": "\u12d0\u1262\u12ed",
        "source_rule": "fere_geez.ch4.anqets.kalay",
    },
    "subjunctive": {
        "name": "\u12d8\u1295\u12f5",
        "geez_name": "\u12d8\u1295\u12f5 \u12a0\u1295\u1240\u133d",
        "rank": "\u1295\u12d1\u1235",
        "source_rule": "fere_geez.ch4.anqets.zend",
    },
    "imperative": {
        "name": "\u1275\u12a5\u12db\u12dd",
        "geez_name": "\u1275\u12a5\u12db\u12dd \u12a0\u1295\u1240\u133d",
        "rank": "\u12d0\u1262\u12ed",
        "source_rule": "fere_geez.ch4.anqets.teizaz",
    },
    "infinitive": {
        "name": "\u12a0\u122d\u12a5\u1235\u1275",
        "geez_name": "\u12a0\u122d\u12a5\u1235\u1275",
        "rank": "\u1295\u12d1\u1235",
        "source_rule": "fere_geez.ch4.anqets.arist",
    },
    "derived_noun": {
        "name": "\u1325\u122c \u12d8\u122d",
        "geez_name": "\u1325\u122c \u12d8\u122d / \u1235\u121d\u12d5",
        "rank": "\u1295\u12d1\u1235",
        "source_rule": "fere_geez.ch4.tire_zer",
    },
    "noun": {
        "name": "\u1235\u121d",
        "geez_name": "\u1235\u121d",
        "rank": "\u1295\u12d1\u1235",
        "source_rule": "fere_geez.ch4.sem",
    },
    "particle_phrase": {
        "name": "\u1290\u1263\u122d",
        "geez_name": "\u1290\u1263\u122d",
        "rank": "\u1290\u1263\u122d",
        "source_rule": "fere_geez.ch3.nabar",
    },
}

WORD_CLASS_GEEZ = {
    "gis": "\u130d\u1235",
    "sem": "\u1235\u121d",
    "nabar": "\u1290\u1263\u122d",
    "qetsel": "\u1245\u133d\u120d",
    "merahiyan": "\u1218\u122b\u1205\u12eb\u1295",
    "arist": "\u12a0\u122d\u12a5\u1235\u1275",
}


def structural_features(form: str, *, stem: str | None = None) -> dict:
    """Order/skeleton features: pure Unicode math, no lexicon."""
    form = form or ""
    stem = stem if stem is not None else form
    skel = get_consonant_skeleton(form)
    bases = [devowelize(c) for c in form]
    orders = [get_char_order(c) for c in form]
    skel_len = len(skel)
    c1_order = orders[0] if orders else 0
    c2_order = orders[1] if len(orders) > 1 else 0
    c3_order = orders[2] if len(orders) > 2 else 0
    laryngeal_positions = [
        i for i, b in enumerate(bases) if b in LARYNGEALS
    ]
    laryngeal_middle = skel_len >= 2 and bases[1] in LARYNGEALS
    hollow = skel_len >= 2 and bases[1] in WEAK_CONSONANTS
    # Collapsed hollow citation (ቆመ): biliteral with C1 in 7th order.
    hollow_collapsed = skel_len == 2 and c1_order == 7
    geminate_signal = skel_len >= 3 and bases[1] == bases[2]
    ends_geez = bool(form) and get_char_order(form[-1]) == 1
    starts_a = bool(form) and devowelize(form[0]) == "\u12a0"
    home = detect_verb_home(skel, stem or form) if form else {}
    return {
        "form": form,
        "skeleton": skel,
        "skel_len": skel_len,
        "letter_count": len(form),
        "orders": orders,
        "c1_order": c1_order,
        "c2_order": c2_order,
        "c3_order": c3_order,
        "ends_geez": ends_geez,
        "laryngeal_middle": laryngeal_middle,
        "laryngeal_positions": laryngeal_positions,
        "hollow": hollow,
        "hollow_collapsed": hollow_collapsed,
        "geminate_signal": geminate_signal,
        "starts_a_extended": starts_a and skel_len >= 4,
        "quadriliteral": skel_len >= 4,
        "verb_home_type": home.get("type"),
        "source_rule": "fere_geez.ch4.merahut_orders",
    }


def classify_army_head(
    root: str,
    *,
    stem: str | None = None,
    verb_home_type: str | None = None,
) -> dict | None:
    """Map structural shape → ሠራዊት አለቃ template (no member lists)."""
    if not root:
        return None
    root_n = normalize_geez(root)
    # Template self-identity (the eight head names are scientific constants).
    for head, info in ARMY_HEADS.items():
        if root_n == normalize_geez(head) or root == head:
            return {
                "head": head,
                "geez_name": info["geez_name"],
                "english_name": info["english_name"],
                "source_rule": info["source_rule"],
                "by": "template_identity",
            }

    feat = structural_features(root, stem=stem)
    home = verb_home_type or feat.get("verb_home_type")

    def _pack(head: str, by: str) -> dict:
        info = ARMY_HEADS[head]
        return {
            "head": head,
            "geez_name": info["geez_name"],
            "english_name": info["english_name"],
            "source_rule": info["source_rule"],
            "by": by,
        }

    # Priority decision tree (Fere Ge'ez §4.3 shape templates).
    if feat["hollow"] or feat["hollow_collapsed"]:
        return _pack("\u1246\u1218", "hollow_or_collapsed")
    if feat["skel_len"] == 2 and feat["ends_geez"]:
        return _pack("\u1224\u1218", "biliteral")
    # ብህለ is the army-head template itself (matched above), not every
    # laryngeal-middle verb. The bihla table is only for ብህለ reductions.
    if feat["quadriliteral"] or feat["starts_a_extended"]:
        return _pack("\u12a0\u12a5\u1218\u1228", "quadriliteral_or_a_extended")
    if home in {"type_c", "type_c_o"} or feat["c1_order"] in {4, 7}:
        return _pack("\u1263\u1228\u12a8", "type_c_c1_order")
    if home == "type_b" or feat["geminate_signal"] or feat["c1_order"] == 5:
        return _pack("\u1240\u12f0\u1230", "type_b_or_geminate")
    if feat["skel_len"] == 3 and feat["c2_order"] == 6:
        return _pack("\u1308\u1265\u1228", "gabra_c2_sadis")
    if feat["skel_len"] == 3 and feat["ends_geez"]:
        return _pack("\u1240\u1270\u1208", "strong_triliteral")
    return None


def detect_asraw_markers(prefixes: list[str] | None, stem: str = "") -> list[str]:
    prefixes = prefixes or []
    found: list[str] = []
    checks = [
        (
            "\u12e8",
            lambda: any(
                p.startswith("\u12e8") or p.startswith("\u12eb") or p.startswith("\u12ed")
                for p in prefixes
            ),
        ),
        (
            "\u1270",
            lambda: any(p.startswith("\u1270") or p.startswith("\u1275") for p in prefixes),
        ),
        (
            "\u12a0",
            lambda: any(
                p == "\u12a0"
                or p.startswith("\u12a0")
                or p.startswith("\u12a5")
                or p.startswith("\u12a2")
                for p in prefixes
            ),
        ),
        (
            "\u1290",
            lambda: any(p.startswith("\u1290") or p.startswith("\u1295") for p in prefixes),
        ),
    ]
    for marker, pred in checks:
        if pred() and marker not in found:
            found.append(marker)
    return found


def _revowel_orders(bases: list[str], orders: list[int]) -> str:
    return "".join(get_char_by_order(b, o) for b, o in zip(bases, orders))


def restore_citation_root(stem: str) -> dict:
    """Restore citation by order math (no lexicon).

    Paper: citation ends in Ge'ez order; length 2-7; keep house shape
    (gabra keeps C2 sadis; type-A derived stems restore to CaCaCa).
    """
    if not stem:
        return {"citation": stem, "by": "empty", "source_rule": "fere_geez.ch4.citation_restore"}
    orders = [get_char_order(c) for c in stem]
    bases = [devowelize(c) for c in stem]
    n = len(stem)
    constraints = citation_constraints(stem)

    if n == 2 and orders[0] == 7:
        citation = _revowel_orders([bases[0], "ወ", bases[1]], [1, 1, 1])
        return {"citation": citation, "by": "hollow_w_from_7th", "source_rule": "fere_geez.ch4.citation_restore.hollow_w"}
    if n == 2 and orders[0] in {3, 5}:
        citation = _revowel_orders([bases[0], "የ", bases[1]], [1, 1, 1])
        return {"citation": citation, "by": "hollow_y_from_3_5", "source_rule": "fere_geez.ch4.citation_restore.hollow_y"}
    if n == 2 and orders[0] == 6 and bases[0] == "በ" and bases[1] == "ለ":
        # ብህለ army-head reduction only (ብሉ / ብል). Not every sadis-initial
        # biliteral: ይቤ, ሕግ, ንግ must not gain a spurious ሀ.
        citation = _revowel_orders([bases[0], "ሀ", bases[1]], [6, 6, 1])
        return {"citation": citation, "by": "bihla_from_dropped_c2", "source_rule": "fere_geez.ch4.citation_restore.bihla_drop"}

    if n == 3 and bases[1] in {"ወ", "የ"} and orders != [1, 1, 1]:
        citation = _revowel_orders(bases, [1, 1, 1])
        kind = "hollow_w_full" if bases[1] == "ወ" else "hollow_y_full"
        return {
            "citation": citation,
            "by": kind,
            "source_rule": "fere_geez.ch4.citation_restore." + kind,
        }
    if n == 2 and orders[-1] == 1 and orders[0] not in {1, 3, 5, 6, 7}:
        citation = _revowel_orders(bases, [1, 1])
        return {
            "citation": citation,
            "by": "biliteral_geez_citation",
            "source_rule": "fere_geez.ch4.citation_restore.biliteral",
        }
    # ብህለ house (fere_geez nǝʿus / ocrpage-045):
    # C2 laryngeal stays in አንቀጽ stems (ብህል → citation).
    # Bug 5 guard: do NOT apply bihla reconstruction to stems already in
    # citation form [1,1,1] (e.g. መሐረ). The bihla pattern is for anqets
    # stems, not for mangling valid laryngeal-middle citations.
    if n == 3 and bases[1] in LARYNGEALS and orders != [1, 1, 1]:
        # Weak-final (C3 ወ/የ) already in Ge'ez on C1 and C2: ጸሐይ → ጸሐየ.
        # Bihla teizaz (በሀል) has a strong C3, so it still falls through.
        if (
            bases[2] in WEAK_CONSONANTS
            and orders[0] == 1
            and orders[1] == 1
            and orders[2] == 6
        ):
            return {
                "citation": _revowel_orders(bases, [1, 1, 1]),
                "by": "weak_final_from_sadis_c3",
                "source_rule": "fere_geez.ch4.citation_restore.weak_final",
            }
        citation = _revowel_orders(bases, [6, 6, 1])
        if stem == citation or orders == [6, 6, 1]:
            return {
                "citation": citation,
                "by": "keep_laryngeal_middle",
                "source_rule": "fere_geez.ch4.army_heads.bihla",
            }
        return {
            "citation": citation,
            "by": "bihla_from_anqets_stem",
            "source_rule": "fere_geez.ch4.anqets.bihla.ocrpage045",
        }

    if n == 3 and orders[-1] == 1:
        # Laryngeal-middle house (ብህለ): keep C2 laryngeal; do not flatten to CaCaCa
        if bases[1] in LARYNGEALS:
            return {"citation": stem, "by": "keep_laryngeal_middle", "source_rule": "fere_geez.ch4.citation_restore.bihla"}
        # Gabra citation: C1 geez, C2 sadis, C3 geez
        if orders[0] == 1 and orders[1] == 6:
            return {"citation": stem, "by": "keep_gabra_shape", "source_rule": "fere_geez.ch4.citation_restore.gabra"}
        if orders[0] in {4, 7}:
            return {"citation": stem, "by": "keep_type_c_shape", "source_rule": "fere_geez.ch4.citation_restore.type_c"}
        if orders == [1, 1, 1]:
            return {"citation": stem, "by": "keep_geez_citation", "source_rule": "fere_geez.ch4.citation_restore.halafi"}
        # Derived/imperfect stem with sadis radicals → type-A CaCaCa
        if orders[1] == 6:
            citation = _revowel_orders(bases, [1, 1, 1])
            return {"citation": citation, "by": "type_a_from_sadis_stem", "source_rule": "fere_geez.ch4.citation_restore.type_a"}
        return {"citation": stem, "by": "keep_ends_geez", "source_rule": "fere_geez.ch4.citation_restore"}

    # Triliteral stems that are not already a Ge'ez-final citation.
    # Classes are vowel-order patterns, not lemma lists.

    # qitāl / qital noun: C1 salis (i-vowel) and C3 sadis.
    # ፊደል [3, 1, 6] and any other consonants in that class → CaCaCa.
    if n == 3 and orders[0] == 3 and orders[2] == 6 and orders[1] in {1, 4}:
        return {
            "citation": _revowel_orders(bases, [1, 1, 1]),
            "by": "qital_noun",
            "source_rule": "fere_geez.ch4.citation_restore.qital",
        }

    # III-laryngeal imperfect: C2 rabəʿ (a) and C3 a bare laryngeal.
    # ኀጣእ → ኀጥአ (guttural perfect: C2 sadis, laryngeal in Ge'ez order).
    if (
        n == 3
        and orders[1] == 4
        and orders[2] == 6
        and bases[2] in LARYNGEALS
    ):
        return {
            "citation": _revowel_orders(bases, [1, 6, 1]),
            "by": "laryngeal_final_from_a_stem",
            "source_rule": "fere_geez.ch4.citation_restore.laryngeal_final",
        }

    # qəddāse abstract noun: C1 sadis, C3 ḥams (-e). ቅዳሴ → CaCaCa.
    if n == 3 and orders[0] == 6 and orders[2] == 5:
        return {
            "citation": _revowel_orders(bases, [1, 1, 1]),
            "by": "qiddase_noun",
            "source_rule": "fere_geez.ch4.citation_restore.qiddase",
        }

    # qətul participle: C1 sadis, C2 kaʿeb (u), C3 sadis. ዝሙር → CaCaCa.
    if n == 3 and orders[0] == 6 and orders[1] == 2 and orders[2] == 6:
        return {
            "citation": _revowel_orders(bases, [1, 1, 1]),
            "by": "qatul_participle",
            "source_rule": "fere_geez.ch4.citation_restore.qatul",
        }

    # Final kaʿeb (u) is a fused plural vowel, not a lexical order.
    # ቀተሉ [1, 1, 2] and ወርዱ [1, 6, 2]. Type-C C1 (4 or 7) is not this class.
    if n == 3 and orders[2] == 2 and orders[0] not in {4, 7}:
        return {
            "citation": _revowel_orders(bases, [1, 1, 1]),
            "by": "citation_from_imperfective_u",
            "source_rule": "fere_geez.ch4.citation_restore.revowelize",
        }

    # C2 and C3 both sadis: split by C1 order and gemination, not by a tuple.
    if n == 3 and orders[1] == 6 and orders[2] == 6:
        if bases[1] == bases[2]:
            # Type-B geminate written twice (ኳንን). Citation vowels are Ge'ez;
            # a 4th-order labiovelar C1 falls back to its order-1 base (ኰ).
            return {
                "citation": _revowel_orders(bases, [1, 1, 1]),
                "by": "geminate_from_sadis_stem",
                "source_rule": "fere_geez.ch4.citation_restore.geminate",
            }
        if orders[0] in {1, 2, 3, 5, 6}:
            # ካልዓይ [1, 6, 6], ዘንድ [6, 6, 6], and other non-a C1.
            return {
                "citation": _revowel_orders(bases, [1, 1, 1]),
                "by": "type_a_from_sadis_pair",
                "source_rule": "fere_geez.ch4.citation_restore.kalay",
            }
        # C1 rabəʿ or sābəʿ, distinct radicals: gabra stem (ጋብር → ገብረ).
        return {
            "citation": _revowel_orders(bases, [1, 6, 1]),
            "by": "gabra_from_cc_sadis_stem",
            "source_rule": "fere_geez.ch4.citation_restore.gabra_stem",
        }

    # Perfective before an object clitic: C1 and C2 Ge'ez, C3 sadis (ቀተል).
    if n == 3 and orders[0] == 1 and orders[1] == 1 and orders[2] == 6:
        return {
            "citation": _revowel_orders(bases, [1, 1, 1]),
            "by": "type_a_from_perfective_stem",
            "source_rule": "fere_geez.ch4.citation_restore.perfective_stem",
        }

    # Quadriliteral with medial sadis pair (C2 and C3). The last radical may
    # carry any real vowel, not only Ge'ez order (ደንግጸ, ደንግጺ). A final sadis
    # is a consonant-final noun (መንግስ), not this stem.
    if (
        n == 4
        and orders[1] == 6
        and orders[2] == 6
        and orders[3] in {1, 2, 3, 4, 5, 7}
    ):
        return {
            "citation": _revowel_orders(bases, [1, 1, 1, 1]),
            "by": "quadriliteral_from_sadis_stem",
            "source_rule": "fere_geez.ch4.citation_restore.quadriliteral",
        }

    if constraints["length_ok"] and constraints["ends_in_geez_order"]:
        return {"citation": stem, "by": "keep_citation_constraints", "source_rule": "fere_geez.ch4.citation_restore"}

    # Non-citation surfaces (e.g. integral ስም): keep form; never invent a fake verbal root.

    return {
        "citation": stem,
        "by": "keep_surface_nonverbal",
        "source_rule": "fere_geez.ch3.nabar.no_forced_root",
    }


def grammar_root_compatible(surface: str, grammar_root: str) -> bool:
    """Reject grammar hits that do not share the surface's first radical."""
    if not surface or not grammar_root:
        return False
    return devowelize(surface[0]) == devowelize(grammar_root[0])


def looks_like_verbal_citation(word: str) -> bool:
    """True for unaffixed house/citation shapes (2–4 letters, Ge'ez-final)."""
    if not word:
        return False
    # Army-head template identity (incl. አእመረ, ባረከ, ገብረ, …)
    if word in ARMY_HEADS or normalize_geez(word) in {
        normalize_geez(h) for h in ARMY_HEADS
    }:
        return True
    n = len(word)
    orders = [get_char_order(c) for c in word]
    if n == 2 and orders[-1] == 1:
        return True
    if n == 3 and orders[-1] == 1:
        if orders == [1, 1, 1]:
            return True
        if orders[0] == 1 and orders[1] == 6:
            return True  # ገብረ house
        if orders[0] in {4, 7}:
            return True  # ባረከ / type-C house
        if devowelize(word[1]) in LARYNGEALS:
            return True  # ብህለ house
    return False


def looks_like_conjugated_stem(stem: str) -> bool:
    """Stem shapes that host object clitics without an overt asraw letter."""
    if not stem or len(stem) < 3:
        return False
    orders = [get_char_order(c) for c in stem]
    if len(stem) == 3 and tuple(orders) in {(1, 1, 6), (1, 6, 6), (6, 6, 6)}:
        return True
    # Longer stacks after a first object letter (ቀተልከ before ኒ).
    if len(stem) >= 4 and orders[0] in {1, 6} and 6 in orders[:3]:
        return True
    return False


def suffix_strip_allowed(
    suffix: str,
    *,
    prefixes: list | None,
    remaining: str | None = None,
    current_word: str | None = None,
) -> bool:
    """Context-sensitive object clitics need a verbal prefix or conjugated stem."""
    prefixes = prefixes or []
    if suffix not in CONTEXT_SENSITIVE_SUFFIXES:
        return True
    if prefixes:
        return True
    if not remaining:
        return False
    # አ/ተ + triliteral citation (አመለከ, ተቀተለከ): final letter is a radical.
    if (
        current_word
        and len(current_word) >= 4
        and current_word[0] in {"አ", "ተ"}
        and looks_like_verbal_citation(current_word[1:])
    ):
        return False
    # Quadriliteral citation of shape 1-2-3-2 (all Ge'ez orders, C4 repeats C2).
    # The final letter is a radical (መነገነ), not an object clitic (ቀተለነ).
    if current_word and len(current_word) == 4:
        word_orders = [get_char_order(c) for c in current_word]
        word_bases = [devowelize(c) for c in current_word]
        if (
            all(o == 1 for o in word_orders)
            and word_bases[3] == word_bases[1]
            and word_bases[1] not in {word_bases[0], word_bases[2]}
        ):
            return False
    # Bare perfective/gabra + object (ሀውጸ+ነ, ቀተለ+ከ).
    if looks_like_verbal_citation(remaining):
        return True
    # Perfective/object stacks (ቀተል+ከ / ቀተልከ+ኒ), not integral አምላክ.
    return looks_like_conjugated_stem(remaining)




# Surface realizations of አሥራው ቀለማት (fere_geez): የ/ተ/አ/ነ → ይ/ት/እ/ን
ASRAW_SURFACE_FORMS = ('ይ', 'ት', 'እ', 'ን')


def _is_bihla_citation(citation: str, bases: list[str]) -> bool:
    """True only for the ብህለ army head, not every C2 laryngeal."""
    if len(bases) != 3:
        return False
    if normalize_geez(citation) == normalize_geez("ብህለ"):
        return True
    return bases[0] == "በ" and bases[1] == "ሀ" and bases[2] == "ለ"


def anqets_transforms_bihla(citation: str) -> dict:
    """ንዑስ እርባታ for ብህለ, fere_geez ocrpage-045.

    Other laryngeal-middle citations keep their own C2. Forcing C2 to ሀ
    turned መሓረ into ምህረ and ውእቱ into ውእተ.
    """
    bases = [devowelize(c) for c in citation]
    if len(bases) != 3:
        raise ValueError("bihla citation must be triliteral")
    if _is_bihla_citation(citation, bases):
        bases = [bases[0], "ሀ", bases[2]]
        halafi = _revowel_orders(bases, [6, 6, 1])
    else:
        halafi = citation
    kalay_stem = _revowel_orders(bases, [6, 6, 6])
    kalay_stem_ha = _revowel_orders(bases, [6, 1, 6])
    kalay_stem_pl = _revowel_orders(bases, [6, 6, 2])
    kalay_stem_ha_pl = _revowel_orders(bases, [6, 1, 2])
    teizaz = _revowel_orders(bases, [1, 1, 6])
    teizaz_pl = _revowel_orders(bases, [1, 1, 2])
    return {
        "halafi": halafi,
        "kalay": 'ይ' + kalay_stem,
        "kalay_pl": 'ይ' + kalay_stem_pl,
        "kalay_ha": 'ይ' + kalay_stem_ha,
        "kalay_ha_pl": 'ይ' + kalay_stem_ha_pl,
        "kalay_stem": kalay_stem,
        "kalay_stem_pl": kalay_stem_pl,
        "kalay_stem_ha": kalay_stem_ha,
        "zend": 'ይ' + kalay_stem,
        "zend_stem": kalay_stem,
        "teizaz": teizaz,
        "teizaz_pl": teizaz_pl,
        "source_rule": "fere_geez.ch4.anqets.bihla.ocrpage045",
    }


def analyze_surface_pdf(surface: str) -> dict | None:
    """Primary PDF path: optional አሥራው → አንቀጽ stem → citation."""
    if not surface:
        return None

    trials: list[tuple[str, list[str]]] = [(surface, [])]
    surf_orders = [get_char_order(c) for c in surface]
    # Triliteral ካልዓይ/ዘንድ stems (ንግር, ከትም) are not አሥራው+CC.
    intact_anqets_stem = len(surface) == 3 and tuple(surf_orders) in {
        (6, 6, 6), (1, 6, 6)
    }
    for pref in ASRAW_SURFACE_FORMS:
        if intact_anqets_stem:
            break
        if surface.startswith(pref) and len(surface) > len(pref):
            trials.append((surface[len(pref):], [pref]))

    bihla_head = 'ብህለ'
    table = anqets_transforms_bihla(bihla_head)
    surf_n = normalize_geez(surface)
    for key, form in table.items():
        if key == "source_rule":
            continue
        if surface == form or surf_n == normalize_geez(form):
            prefs: list[str] = []
            stem = form
            for pref in ASRAW_SURFACE_FORMS:
                if form.startswith(pref):
                    prefs = [pref]
                    stem = form[len(pref):]
                    break
            return {
                "citation": bihla_head,
                "stem": stem,
                "prefixes": prefs,
                "suffixes": [],
                "anqets_key": key,
                "army_head": bihla_head,
                "by": "pdf_table_match_bihla",
                "source_rule": table["source_rule"],
            }

    for stem, prefs in trials:
        if not stem:
            continue
        orders = [get_char_order(c) for c in stem]
        bases = [devowelize(c) for c in stem]
        if len(stem) == 3 and _is_bihla_citation(stem, bases):
            citation = _revowel_orders([bases[0], "ሀ", bases[2]], [6, 6, 1])
            return {
                "citation": citation,
                "stem": stem,
                "prefixes": prefs,
                "suffixes": [],
                "anqets_key": "kalay_stem" if prefs else "halafi",
                "army_head": bihla_head,
                "by": "pdf_asraw_bihla_stem",
                "source_rule": "fere_geez.ch4.anqets.bihla.ocrpage045",
            }
        # Reduced writing after አሥራው only for ብህለ (ይብሉ / ይብል), not every CəC.
        if (
            prefs
            and prefs[0] in {"ይ", "ት", "እ"}
            and len(stem) == 2
            and orders[0] == 6
            and bases[0] == "በ"
            and bases[1] == "ለ"
        ):
            citation = _revowel_orders([bases[0], 'ሀ', bases[1]], [6, 6, 1])
            return {
                "citation": citation,
                "stem": stem,
                "prefixes": prefs,
                "suffixes": [],
                "anqets_key": "kalay_reduced",
                "army_head": bihla_head,
                "by": "pdf_asraw_bihla_template_c2",
                "source_rule": "fere_geez.ch4.army_heads.bihla+asraw",
            }
    return None


def anqets_transforms(citation: str) -> dict | None:
    """Generative ኃላፊ/ካልዓይ/ዘንድ/ትእዛዝ for strong triliteral citations."""
    if not citation:
        return None
    skel = get_consonant_skeleton(citation)
    if len(skel) != 3:
        return None
    if not citation_constraints(citation)["ends_in_geez_order"]:
        return None
    bases = [devowelize(c) for c in skel]
    if len(bases) != 3:
        return None

    if _is_bihla_citation(citation, bases):
        return anqets_transforms_bihla(citation)

    # Laryngeal-middle citations that are not ብህለ keep their own halafi
    # (መሓረ stays መሓረ; do not rewrite C2 to ሀ as ምህረ).
    if bases[1] in LARYNGEALS:
        halafi = citation
    else:
        halafi = _revowel_orders(bases, [1, 1, 1])
    kalay_stem = _revowel_orders(bases, [1, 6, 6])
    zend_stem = _revowel_orders(bases, [6, 6, 6])
    teizaz = zend_stem
    ye = "\u12ed"
    return {
        "halafi": halafi,
        "kalay": ye + kalay_stem,
        "kalay_stem": kalay_stem,
        "zend": ye + zend_stem,
        "zend_stem": zend_stem,
        "teizaz": teizaz,
        "source_rule": "fere_geez.ch4.anqets.transforms.qatala",
    }


def arist_transforms(citation: str) -> dict | None:
    """Generate አርእስት / ውስጠ ዘ shapes from a triliteral citation."""
    skel = get_consonant_skeleton(citation)
    if len(skel) != 3:
        return None
    bases = [devowelize(c) for c in skel]
    return {
        "qatul": _revowel_orders(bases, [6, 2, 6]),   # ቅቱል
        "qatali": _revowel_orders(bases, [1, 4, 3]),  # ቀታሊ
        "source_rule": "fere_geez.ch4.arist_weste_ze",
    }


def match_anqets_surface(surface: str, citation: str) -> dict | None:
    """Name a surface form by matching generative አንቀጽ candidates."""
    transforms = anqets_transforms(citation)
    if not transforms:
        return None
    surf = normalize_geez(surface)
    mapping = [
        ("halafi", "perfective", transforms["halafi"]),
        ("kalay", "imperfective", transforms["kalay"]),
        ("kalay", "imperfective", transforms["kalay_stem"]),
        ("zend", "subjunctive", transforms["zend"]),
        ("zend", "subjunctive", transforms["zend_stem"]),
        ("teizaz", "imperative", transforms["teizaz"]),
    ]
    for key, pattern_name, candidate in mapping:
        if surf == normalize_geez(candidate) or surface == candidate:
            info = dict(ANQETS_BY_PATTERN[pattern_name])
            info["matched_key"] = key
            info["matched_form"] = candidate
            info["source_rule"] = transforms["source_rule"]
            return info
    return None


def detect_balabet_suffix(word: str) -> str | None:
    if not word:
        return None
    # Citations whose final radical equals a ባለቤት letter (መለከ, ባረከ)
    # are verbs/nouns, not possessive surfaces.
    if looks_like_verbal_citation(word):
        return None
    for suf in sorted(BALABET_SUFFIXES, key=len, reverse=True):
        if word.endswith(suf) and len(word) > len(suf):
            remaining = word[: -len(suf)]
            if len(get_consonant_skeleton(remaining)) < 2:
                continue
            # Final radical of a shorter citation is not ባለቤት (አመለ+ከ).
            if looks_like_verbal_citation(remaining):
                continue
            return suf
    return None


def is_merahiyan(form: str) -> bool:
    return form in MERAHIYAN_FORMS or normalize_geez(form) in {
        normalize_geez(m) for m in MERAHIYAN_FORMS
    }


def looks_like_qetsel(form: str, features: dict) -> bool:
    """Lightweight attributive seed (geezgram ቅጽል): shape only, no word list."""
    if not form or features.get("skel_len", 0) < 2:
        return False
    # Common attributive endings in 6th/3rd order without full verbal አሥራው path.
    last_order = get_char_order(form[-1])
    if last_order in {3, 6} and not features.get("ends_geez"):
        return True
    return False


def classify_word_class(
    *,
    root: str,
    stem: str,
    prefixes: list[str] | None,
    suffixes: list[str] | None,
    pattern_name: str | None,
    method: str | None,
    in_lexicon_verbs: bool,
    in_nouns: bool,
    noun_has_verbal_root: bool,
    features: dict | None = None,
) -> dict:
    prefixes = prefixes or []
    suffixes = suffixes or []
    features = features or structural_features(root or stem, stem=stem)
    asraw = detect_asraw_markers(prefixes, stem)
    surface = stem or root

    if method in {"particle", "particle_phrase"}:
        if is_merahiyan(surface) or any(is_merahiyan(p) for p in (root or "").split(" + ")):
            return {
                "word_class": "merahiyan",
                "geez_name": WORD_CLASS_GEEZ["merahiyan"],
                "source_rule": "fere_geez.ch2.merahiyan",
            }
        return {
            "word_class": "nabar",
            "geez_name": WORD_CLASS_GEEZ["nabar"],
            "source_rule": "fere_geez.ch3.nabar",
        }

    if is_merahiyan(surface) or is_merahiyan(root):
        return {
            "word_class": "merahiyan",
            "geez_name": WORD_CLASS_GEEZ["merahiyan"],
            "source_rule": "fere_geez.ch2.merahiyan",
        }

    arist = arist_transforms(root) if root else None
    if arist and any(
        normalize_geez(surface) == normalize_geez(v)
        for k, v in arist.items()
        if k != "source_rule"
    ):
        return {
            "word_class": "arist",
            "geez_name": WORD_CLASS_GEEZ["arist"],
            "source_rule": arist["source_rule"],
        }

    if pattern_name == "derived_noun" or (
        in_nouns and noun_has_verbal_root
    ) or pattern_name == "infinitive":
        return {
            "word_class": "sem",
            "geez_name": WORD_CLASS_GEEZ["sem"],
            "source_rule": "fere_geez.ch4.tire_zer",
        }

    if pattern_name == "noun" or (in_nouns and not noun_has_verbal_root):
        return {
            "word_class": "sem",
            "geez_name": WORD_CLASS_GEEZ["sem"],
            "source_rule": "fere_geez.ch4.sem.integral",
        }

    # Object clitics overlap ባለቤት letters (ከ/ነ); only true possessive
    # operators (or surface detect) mark ስም.
    possessive_hits = [
        s for s in suffixes
        if s in BALABET_SUFFIXES and s not in CONTEXT_SENSITIVE_SUFFIXES
    ]
    if possessive_hits or detect_balabet_suffix(surface):
        if not asraw and not in_lexicon_verbs:
            return {
                "word_class": "sem",
                "geez_name": WORD_CLASS_GEEZ["sem"],
                "source_rule": "fere_geez.ch4.balabet",
            }

    matched = match_anqets_surface(surface, root) if root else None
    verbal_patterns = {
        "perfective", "imperfective", "subjunctive", "imperative",
        "causative", "passive", "causative_passive",
        "causative_imperfective", "causative_perfective",
        "passive_imperfective", "passive_perfective",
        "causative_passive_imperfective", "causative_passive_perfective",
        "causative_jussive", "causative_passive_jussive",
    }
    if asraw or matched or pattern_name in verbal_patterns or in_lexicon_verbs:
        return {
            "word_class": "gis",
            "geez_name": WORD_CLASS_GEEZ["gis"],
            "source_rule": "fere_geez.ch4.abat_zer",
        }

    constraints = citation_constraints(root or surface)
    if constraints["length_ok"] and constraints["ends_in_geez_order"] and features["skel_len"] >= 2:
        return {
            "word_class": "gis",
            "geez_name": WORD_CLASS_GEEZ["gis"],
            "source_rule": "fere_geez.ch4.abat_zer.geez_ending",
        }

    if looks_like_qetsel(surface, features):
        return {
            "word_class": "qetsel",
            "geez_name": WORD_CLASS_GEEZ["qetsel"],
            "source_rule": "geezgram.vol1.qetsel.shape",
        }

    return {
        "word_class": "nabar",
        "geez_name": WORD_CLASS_GEEZ["nabar"],
        "source_rule": "fere_geez.ch3.nabar.default",
    }


def anqets_for_pattern(pattern: dict | None) -> dict | None:
    if not pattern:
        return None
    name = pattern.get("name")
    info = ANQETS_BY_PATTERN.get(name)
    if not info:
        if pattern.get("geez_name"):
            return {
                "name": pattern.get("geez_name"),
                "geez_name": pattern.get("geez_name"),
                "rank": None,
                "source_rule": "stemmer.identify_verb_pattern",
            }
        return None
    return dict(info)


def classify_root_class(
    *,
    root: str,
    root_type: str | None,
    pattern_name: str | None,
    method: str | None,
    in_lexicon_verbs: bool,
    in_nouns: bool,
    noun_has_verbal_root: bool,
    word_class: str | None = None,
    features: dict | None = None,
    has_anqets_match: bool = False,
    has_asraw: bool = False,
) -> dict:
    """Capacity-based ontology: አባት ዘር / ጥሬ ዘር / ነባር."""
    if word_class == "arist" or pattern_name == "infinitive":
        return {
            "root_class": "tire_zer",
            "geez_name": "\u1325\u122c \u12d8\u122d",
            "source_rule": "fere_geez.ch4.arist",
        }
    if word_class == "sem" or pattern_name == "derived_noun" or root_type == "derived_noun" or (
        in_nouns and noun_has_verbal_root
    ):
        return {
            "root_class": "tire_zer",
            "geez_name": "\u1325\u122c \u12d8\u122d",
            "source_rule": "fere_geez.ch4.tire_zer",
        }
    if word_class in {"nabar", "merahiyan", "qetsel"} or method in {
        "particle", "particle_phrase"
    }:
        return {
            "root_class": "nabar",
            "geez_name": "\u1290\u1263\u122d",
            "source_rule": "fere_geez.ch3.nabar",
        }
    if pattern_name == "noun" or (in_nouns and not noun_has_verbal_root):
        # Integral ስም without verbal root: treat as ነባር capacity (no ዘርነት).
        return {
            "root_class": "nabar",
            "geez_name": "\u1290\u1263\u122d",
            "source_rule": "fere_geez.ch3.nabar.integral_sem",
        }

    constraints = citation_constraints(root)
    can_conjugate = has_anqets_match or has_asraw or in_lexicon_verbs or word_class == "gis"
    if can_conjugate and constraints["length_ok"]:
        return {
            "root_class": "abat_zer",
            "geez_name": "\u12a0\u1263\u1275 \u12d8\u122d",
            "source_rule": "fere_geez.ch4.abat_zer",
        }
    if constraints["ends_in_geez_order"] and constraints["length_ok"]:
        return {
            "root_class": "abat_zer",
            "geez_name": "\u12a0\u1263\u1275 \u12d8\u122d",
            "source_rule": "fere_geez.ch4.abat_zer.geez_ending",
        }
    return {
        "root_class": "nabar",
        "geez_name": "\u1290\u1263\u122d",
        "source_rule": "fere_geez.ch3.nabar.default",
    }


def citation_constraints(root: str) -> dict:
    skel = get_consonant_skeleton(root) if root else ""
    letters = len(root) if root else 0
    ends_geez = bool(root) and get_char_order(root[-1]) == 1
    c1_order = get_char_order(root[0]) if root else 0
    marahut_ok = c1_order in {1, 4, 5, 6, 7} if c1_order else False
    return {
        "letter_count": letters,
        "skeleton_count": len(skel),
        "length_ok": 2 <= letters <= 7 if letters else False,
        "ends_in_geez_order": ends_geez,
        "marahut_start_ok": marahut_ok,
        "source_rule": "fere_geez.ch4.citation_constraints",
    }


def build_classical_analysis(
    *,
    root: str,
    stem: str,
    prefixes: list[str] | None,
    pattern: dict | None,
    root_type: str | None,
    method: str | None,
    in_lexicon_verbs: bool = False,
    in_nouns: bool = False,
    noun_has_verbal_root: bool = False,
    suffixes: list[str] | None = None,
    surface: str | None = None,
) -> dict:
    prefixes = prefixes or []
    suffixes = suffixes or []
    pattern = pattern or {}
    stem = stem or root or ""
    surface = surface or stem
    features = structural_features(root or stem, stem=stem)
    asraw = detect_asraw_markers(prefixes, stem)
    transforms = anqets_transforms(root) if root else None
    matched = match_anqets_surface(surface, root) if root else None
    arist = arist_transforms(root) if root else None
    balabet = detect_balabet_suffix(surface)
    if not balabet:
        for s in suffixes:
            if s in BALABET_SUFFIXES:
                balabet = s
                break

    word_class = classify_word_class(
        root=root,
        stem=stem,
        prefixes=prefixes,
        suffixes=suffixes,
        pattern_name=pattern.get("name"),
        method=method,
        in_lexicon_verbs=in_lexicon_verbs,
        in_nouns=in_nouns,
        noun_has_verbal_root=noun_has_verbal_root,
        features=features,
    )

    army = None
    if word_class["word_class"] == "gis" or (
        word_class["word_class"] in {"sem", "arist"} and noun_has_verbal_root
    ) or in_lexicon_verbs:
        army = classify_army_head(
            root,
            stem=stem,
            verb_home_type=features.get("verb_home_type"),
        )

    anqets = matched or anqets_for_pattern(pattern)
    root_class = classify_root_class(
        root=root,
        root_type=root_type,
        pattern_name=pattern.get("name"),
        method=method,
        in_lexicon_verbs=in_lexicon_verbs,
        in_nouns=in_nouns,
        noun_has_verbal_root=noun_has_verbal_root,
        word_class=word_class["word_class"],
        features=features,
        has_anqets_match=bool(matched),
        has_asraw=bool(asraw),
    )
    constraints = citation_constraints(root)

    source_rules = [word_class["source_rule"], root_class["source_rule"]]
    if army:
        source_rules.append(army["source_rule"])
    if anqets and anqets.get("source_rule"):
        source_rules.append(anqets["source_rule"])
    if asraw:
        source_rules.append("fere_geez.ch6.asraw_qelamat")
    if balabet:
        source_rules.append("fere_geez.ch4.balabet")
    if arist:
        source_rules.append(arist["source_rule"])
    source_rules.append(constraints["source_rule"])
    source_rules.append(features["source_rule"])

    return {
        "word_class": word_class["word_class"],
        "word_class_geez": word_class["geez_name"],
        "root_class": root_class["root_class"],
        "root_class_geez": root_class["geez_name"],
        "army_head": army["head"] if army else None,
        "army_head_info": army,
        "anqets": anqets,
        "asraw_markers": asraw,
        "anqets_transforms": transforms,
        "arist_transforms": arist,
        "balabet_suffix": balabet,
        "structural_features": features,
        "citation_constraints": constraints,
        "source_rule": source_rules[0],
        "source_rules": list(dict.fromkeys(source_rules)),
    }


def army_head_sources(head: str) -> list[str]:
    info = ARMY_HEADS.get(head)
    if not info:
        return []
    return [info["source_rule"], SECONDARY_SOURCES["geezgram_vol2_army_heads"]]
