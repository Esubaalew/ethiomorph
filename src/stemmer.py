"""
EthioMorph Stemmer - Research-Grade Root Analyzer
=================================================
Extracts triliteral/quadriliteral roots from Ge'ez words.
Outputs full derivation paths for morphological transparency.

This module provides tools to reverse-engineer a conjugated word back to its
lexical root by stripping affixes, normalizing characters, and reconstructing
weak radicals.

Esubalew Chekol
"""

import json
import os
from src.normalizer import normalize_geez
from src.decomposer import get_consonant_skeleton, get_char_order, devowelize, detect_verb_home
from src.grammar_loader import GrammarIndex, PATTERN_CODE_MAP
from src.classical_rules import (
    CITATION_NOUNS,
    NOMINAL_FEMININE_ENDINGS,
    build_classical_analysis,
    classify_army_head,
    grammar_root_compatible,
    analyze_surface_pdf,
    is_merahiyan,
    looks_like_verbal_citation,
    restore_citation_root,
    suffix_strip_allowed,
)


PARTICLE_LEXICON = {
    'እም': {
        'type': 'preposition',
        'geez_type': 'መታያዥ',
        'english_type': 'Preposition',
        'meaning': 'from / out of',
        'gloss': "'əm",
    },
    'ወ': {
        'type': 'conjunction',
        'geez_type': 'ስምመስር',
        'english_type': 'Conjunction',
        'meaning': 'and',
        'gloss': 'wä',
    },
    'ዝ': {
        'type': 'demonstrative',
        'geez_type': 'አንጻራዊ ተውላጠ ስም',
        'english_type': 'Demonstrative Pronoun',
        'meaning': 'this',
        'gloss': 'zə',
    },
    'በ': {
        'type': 'preposition',
        'geez_type': 'መታያዥ',
        'english_type': 'Preposition',
        'meaning': 'in / with',
        'gloss': 'bä',
    },
    'ለ': {
        'type': 'preposition',
        'geez_type': 'መታያዥ',
        'english_type': 'Preposition',
        'meaning': 'to / for',
        'gloss': 'lä',
    },
    'ከ': {
        'type': 'preposition',
        'geez_type': 'መታያዥ',
        'english_type': 'Preposition',
        'meaning': 'from / than',
        'gloss': 'kä',
    },
    'የ': {
        'type': 'preposition',
        'geez_type': 'መታያዥ',
        'english_type': 'Preposition',
        'meaning': 'of',
        'gloss': 'yä',
    },
}


class GeezStemmer:
    """
    Ge'ez morphological analyzer.
    
    Provides complete derivation paths showing how roots are extracted through 
    normalization, affix stripping, and weak root reconstruction.
    """
    
    def __init__(self):
        """Initialize the stemmer by loading the lexicon."""
        self.particles = PARTICLE_LEXICON
        self.particle_forms = sorted(self.particles.keys(), key=len, reverse=True)
        self.lexicon_roots = {}
        self.weak_initial_roots = set()
        self.hollow_w_roots = set()
        self.hollow_y_roots = set()
        self.quadriliterals = set()
        
        try:
            lexicon_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'lexicon.json')
            with open(lexicon_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for entry in data.get('roots', []):
                    root = entry['root']
                    self.lexicon_roots[root] = entry
                    
                    root_type = entry.get('type', '')
                    if root_type == 'weak_initial':
                        self.weak_initial_roots.add(root)
                    elif root_type == 'quadriliteral':
                        self.quadriliterals.add(root)
                    elif root_type == 'hollow_w':
                        self.hollow_w_roots.add(root)
                    elif root_type == 'hollow_y':
                        self.hollow_y_roots.add(root)

            self.hollow_w_lookup = {
                normalize_geez(root): root for root in self.hollow_w_roots
            }
            self.hollow_y_lookup = {
                normalize_geez(root): root for root in self.hollow_y_roots
            }
            self.lexicon_normalized_lookup = {}
            for lex_root in self.lexicon_roots:
                norm = normalize_geez(lex_root)
                if norm not in self.lexicon_normalized_lookup:
                    self.lexicon_normalized_lookup[norm] = lex_root
            self.skeleton_lookup = {}
            for lex_root in self.lexicon_roots:
                skel = normalize_geez(get_consonant_skeleton(lex_root))
                self.skeleton_lookup.setdefault(skel, []).append(lex_root)
                        
        except FileNotFoundError:
            print("Warning: lexicon.json not found. Using empty lexicon.")
            self.hollow_w_lookup = {}
            self.hollow_y_lookup = {}
            self.lexicon_normalized_lookup = {}
            self.skeleton_lookup = {}

        self.nouns = {}
        try:
            lexicon_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'lexicon.json')
            with open(lexicon_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for entry in data.get('nouns', []):
                    self.nouns[entry['word']] = entry
        except Exception:
            pass

        self.grammar = GrammarIndex()
        if self.grammar.loaded:
            for entry in self.grammar.roots.values():
                root = entry["root"]
                skel = normalize_geez(get_consonant_skeleton(root))
                if root not in self.skeleton_lookup.get(skel, []):
                    self.skeleton_lookup.setdefault(skel, []).append(root)

        self.prefixes = [
            # Stem IV (አስተሳሳቢ) - Causative-Passive fused prefixes (LONGEST FIRST)
            'ያስተ', 'ታስተ', 'ናስተ', 'ላስተ',  # Imperfective/Jussive + አስተ
            # Stem IV base
            'መስተ', 'አስተ',
            # Other compounds
            'እንዘ', 'እለ',
            # Compound causative (ይ+አስ=ያስ) - for አስ-stem verbs  
            'ያስ', 'ታስ', 'ናስ', 'ላስ',
            # Causative fused prefixes (ይ+አ=ያ, ት+አ=ታ, etc.)
            'ያን', 'ታን', 'ናን',  # Stem with አን-
            'ያ', 'ታ', 'ና',      # Stem III causative
            # Passive fused prefixes (ይ+ተ=ይት, etc.)
            'ይት', 'ትት', 'እት', 'ንት',  # Stem II passive imperfective
            # Basic subject prefixes
            'ወ', 'በ', 'ለ', 'ከ', 'የ',
            'ይ', 'ት', 'እ', 'ኢ', 'ን', 'ል',
            # Stem prefixes
            'አን', 'አስ', 'አ', 'ተ', 'መ', 'ም', 'ሳ',
        ]
        
        # Stem prefix classification for pattern detection
        self.stem_prefixes = {
            # Stem IV (Causative-Passive)
            'ያስተ': {'stem': 4, 'name': 'causative_passive_imperfective'},
            'ታስተ': {'stem': 4, 'name': 'causative_passive_imperfective'},
            'ናስተ': {'stem': 4, 'name': 'causative_passive_imperfective'},
            'ላስተ': {'stem': 4, 'name': 'causative_passive_jussive'},
            'አስተ': {'stem': 4, 'name': 'causative_passive_perfective'},
            # Stem III (Causative)
            'ያ': {'stem': 3, 'name': 'causative_imperfective'},
            'ታ': {'stem': 3, 'name': 'causative_imperfective'},
            'ና': {'stem': 3, 'name': 'causative_imperfective'},
            'አ': {'stem': 3, 'name': 'causative_perfective'},
            # Stem II (Passive)
            'ይት': {'stem': 2, 'name': 'passive_imperfective'},
            'ትת': {'stem': 2, 'name': 'passive_imperfective'},
            'ተ': {'stem': 2, 'name': 'passive_perfective'},
        }
        
      
        self.causative_prefixes = {'ያ', 'ታ', 'ና', 'አ', 'ያስተ', 'ታስተ', 'ናስተ', 'አስተ'}
        
        # Laryngeal consonants (ላሪንጅያል) - can disappear in certain conjugations
        self.laryngeals = {'ሀ', 'ሐ', 'ኀ', 'አ', 'ዐ', 'ዓ', 'ህ', 'ሕ', 'ኅ', 'ዕ'}
        
        # Known laryngeal-middle roots (C2 is laryngeal) for reconstruction
        self.laryngeal_middle_roots = {
            'ብህለ': {'meaning': 'to say/speak', 'type': 'laryngeal_middle'},
            'ነአከ': {'meaning': 'to wake up', 'type': 'laryngeal_middle'},
            'መሐረ': {'meaning': 'to forgive', 'type': 'laryngeal_middle'},
            'ሰሐለ': {'meaning': 'to draw', 'type': 'laryngeal_middle'},
            'ለሐየ': {'meaning': 'to flee', 'type': 'laryngeal_middle'},
            'ፈሐመ': {'meaning': 'to understand', 'type': 'laryngeal_middle'},
            'ረሐበ': {'meaning': 'to be hungry', 'type': 'laryngeal_middle'},
            'ደሐየ': {'meaning': 'to be well', 'type': 'laryngeal_middle'},
            'ገሐደ': {'meaning': 'to flee', 'type': 'laryngeal_middle'},
        }
        
        self.suffixes = [
            # Object suffixes (longer first)
            'ክሙ', 'ክን', 'ኦሙ', 'ኦን', 'ዎሙ', 'ዎን',
            # Simple object/subject suffixes
            'ሙ', 'ማ', 'ዎ', 'ዮ', 'ኡ', 'ኣ',
            'ነ', 'ኒ', 'ና', 'ኩ', 'ከ', 'ኪ',
            'ክ', 'ን', 'ም', 'ዩ',
            # Feminine / derived-noun endings: ት and ታ are the same operator
            # at 6th vs 4th order, not a fourth radical.
            *sorted(NOMINAL_FEMININE_ENDINGS, key=len, reverse=True),
        ]
        # Consonant clusters that begin integral roots/nouns, not detachable prefixes.
        # Keep these long enough that አመለከ (causative of መለከ) is not blocked.
        self.prefix_block_starts = (
            'አምላ', 'አምነ', 'አምላክ',
        )

    def _segment_particles(self, word):
        """
        Segment a token into a chain of known particles.

        Uses longest-match backtracking so multi-character particles like እም
        are preferred over single-character overlaps.
        """
        def helper(pos):
            if pos == len(word):
                return []
            for form in self.particle_forms:
                if word.startswith(form, pos):
                    rest = helper(pos + len(form))
                    if rest is not None:
                        return [form] + rest
            return None

        segments = helper(0)
        if not segments:
            return None
        return segments

    def _build_particle_result(self, word, segments, derivation_steps):
        """Build analysis output for an atomic particle phrase."""
        particles = []
        flow_parts = []
        for index, form in enumerate(segments, start=1):
            info = self.particles[form]
            particles.append({
                "form": form,
                "type": info["type"],
                "geez_type": info["geez_type"],
                "english_type": info["english_type"],
                "meaning": info["meaning"],
                "gloss": info["gloss"],
                "position": index,
            })
            flow_parts.append(f"{form} ({info['meaning']})")
            derivation_steps.append({
                "step": len(derivation_steps) + 1,
                "action": "segment_particle",
                "description": f"{info['english_type']}: {info['meaning']}",
                "before": word if index == 1 else None,
                "after": form,
                "rule": f"{info['geez_type']} · {info['gloss']}",
                "particle": form,
                "particle_type": info["type"],
            })

        combined_meaning = " ".join(p["meaning"] for p in particles)
        display_form = " + ".join(p["form"] for p in particles)

        return self._attach_classical_fields(
            {
                "input": word,
                "root": display_form,
                "root_consonants": [],
                "root_type": "particle_phrase",
                "verb_home": None,
                "meaning": combined_meaning,
                "confidence": 0.98,
                "analysis": {
                    "stem": word,
                    "pattern": {
                        "name": "particle_phrase",
                        "geez_name": "አካል ቃላት",
                        "english_name": "Particle Phrase",
                        "description": "Atomic function-word sequence",
                    },
                    "prefixes": [],
                    "suffixes": [],
                    "method": "particle_phrase",
                    "particles": particles,
                    "gloss": combined_meaning,
                    "flow": " → ".join(flow_parts),
                },
                "derivation_path": derivation_steps,
                "research_notation": {
                    "root_display": " + ".join(p["form"] for p in particles),
                    "pattern_formula": "ParticlePhrase(" + " · ".join(p["type"] for p in particles) + ")",
                    "affix_formula": " ".join(p["form"] for p in particles),
                },
            }
        )

    def _is_weak_root_candidate(self, stem):
        """
        Detects if stem shows signs of weak root (hollow or weak initial).
        
        Args:
            stem: The stem to check.
            
        Returns:
            True if candidate for weak root reconstruction.
        """
        if len(stem) < 1:
            return False
        
        first_char_stem = stem[0]
        order = get_char_order(first_char_stem)
        if order in [7, 3, 5]:
            return True
        
        skeleton = get_consonant_skeleton(stem)
        if len(skeleton) == 2:
            candidate = 'ወ' + skeleton
            if candidate in self.weak_initial_roots:
                return True
                
        return False

    def _try_weak_initial_imperfective(self, word):
        """Detect ይ/ት/እ-prefixed imperfective of a weak-initial (ወ) verb.

        E.g. ይሃብ -> (ወሀበ, 'ይ'). Returns (root, prefix) or None.
        The restored root must be a known weak-initial root; this keeps
        the rule from firing on genuine bihla-house stems.
        """
        if len(word) != 3 or word[0] not in ("ይ", "ት", "እ"):
            return None
        stem = word[1:]
        candidate = "ወ" + get_consonant_skeleton(stem)
        if candidate in getattr(self, "weak_initial_roots", set()):
            return candidate, word[0]
        cand_norm = normalize_geez(candidate)
        if cand_norm in getattr(self, "lexicon_normalized_lookup", {}):
            return self.lexicon_normalized_lookup[cand_norm], word[0]
        return None

    def _is_laryngeal_drop_candidate(self, stem):
        """True when a 2-radical stem looks like ብህለ-house C2 drop (C1 sadis)."""
        if not stem:
            return False
        skeleton = get_consonant_skeleton(stem)
        if len(skeleton) != 2:
            return False
        # Hollow uses 7/3/5 on C1. Bihla drop is only the ብህለ template
        # (ብሉ / ብል), not every sadis-initial pair.
        if get_char_order(stem[0]) != 6 or len(stem) < 2:
            return False
        return devowelize(stem[0]) == "በ" and devowelize(stem[1]) == "ለ"

    def _match_pattern_code_label(self, word):
        """
        Match Zewadla dictionary labels: citation + pattern section code.

        E.g. ሰርሐቀተ = ሰርሐ (root) + ቀተ (perfective pattern code).
        These are dictionary metadata, not morphological suffixes, so they
        must be recognized before affix stripping (which would peel ተ as a
        feminine ending). Returns (base, code, pattern_info) or None.

        The base must be a valid root: a lexicon hit or a valid verbal
        citation shape. This guards against false positives on natural words
        that happen to end with a code sequence.
        """
        for code in sorted(PATTERN_CODE_MAP, key=len, reverse=True):
            if not word.endswith(code):
                continue
            base = word[: -len(code)]
            if not base:
                continue
            # Base must be a known root or valid citation shape.
            base_norm = normalize_geez(base)
            is_lexicon_root = (
                base in self.lexicon_roots
                or base_norm in self.lexicon_roots
                or base in self.lexicon_normalized_lookup
                or base_norm in self.lexicon_normalized_lookup
            )
            if is_lexicon_root or looks_like_verbal_citation(base_norm):
                return base, code, PATTERN_CODE_MAP[code]
        return None
    
    def _reconstruct_laryngeal_middle(self, skeleton):
        """
        Reconstruct a laryngeal-middle citation from a 2-consonant stem/skeleton.

        Rule (ብህለ house): dropped C2 is restored as laryngeal at sadis,
        yielding C1ə-Hə-C3a (ብሉ → ብህለ). Order math only, no lemma list.
        """
        from src.decomposer import get_char_by_order
        if not skeleton:
            return None, None
        stem = skeleton
        if len(get_consonant_skeleton(stem)) != 2:
            return None, None
        # Normalize to a 2-letter stem for restore_citation_root.
        if len(stem) != 2:
            sk = get_consonant_skeleton(stem)
            stem = get_char_by_order(devowelize(sk[0]), 6) + get_char_by_order(
                devowelize(sk[1]), 1
            )
        from src.classical_rules import restore_citation_root
        restored = restore_citation_root(stem)
        if restored.get("by") == "bihla_from_dropped_c2":
            return restored["citation"], "ህ"
        return None, None

    def _try_hollow_middle_restore(self, skeleton):
        """
        Restore a hollow middle radical from a 2-consonant skeleton.

        Checks hollow-W before hollow-Y. Uses normalized lexicon matching so
        ሀወረ matches lexicon entry ሐወረ.
        """
        if len(skeleton) != 2:
            return None, None

        candidate_w = skeleton[0] + 'ወ' + skeleton[1]
        restored_w = self.hollow_w_lookup.get(normalize_geez(candidate_w))
        if restored_w:
            return restored_w, "hollow_w"

        candidate_y = skeleton[0] + 'የ' + skeleton[1]
        restored_y = self.hollow_y_lookup.get(normalize_geez(candidate_y))
        if restored_y:
            return restored_y, "hollow_y"

        return None, None

    def _c1_compatible(self, candidate, source):
        """True when candidate and source share C1 vowel order.

        Short surfaces (ልብ, ስም) must not match a different C1 order.
        Triliteral imperatives (ሕወር, C1=6th) may still cite a 1st-order root.
        """
        if not candidate or not source:
            return False
        source_order = get_char_order(source[0])
        cand_order = get_char_order(candidate[0])
        if not source_order or not cand_order:
            return False
        if source_order == cand_order:
            return True
        if len(source) >= 3 and source_order == 6 and cand_order == 1:
            return True
        return False

    def _prefer_citation_orthography(self, candidates, source):
        """Prefer a Ge'ez-order citation, then the spelling closest to the surface.

        Inflected sadis (ደንግጸ) must not beat ደነገጸ. Among real citations,
        መሓረ prefers መሐረ over the fully normalized መሃረ/መሀረ.
        """
        if not candidates:
            return []
        if len(candidates) == 1:
            return list(candidates)

        def score(candidate):
            geez = sum(1 for ch in candidate if get_char_order(ch) == 1)
            ortho = 0
            if source:
                for a, b in zip(candidate, source):
                    if a == b:
                        ortho += 3
                    elif devowelize(a) == devowelize(b):
                        ortho += 1
                if (
                    len(candidate) > 1
                    and len(source) > 1
                    and devowelize(candidate[1]) == devowelize(source[1])
                ):
                    ortho += 2
            return (geez, ortho)

        best = max(score(c) for c in candidates)
        return [c for c in candidates if score(c) == best]

    def _resolve_skeleton_citation(self, skeleton, source=None, stem=None, pattern_name=None):
        """
        Map a devowelized skeleton back to a lexicon citation root.

        Skeletonization collapses vowel order (ጣ/ጥ/ጠ → ጠ) and normalization
        collapses homophone rows (ኀ/ሀ/ሐ → ሀ). The lexicon stores citation
        spellings such as ኀጥአ; this resolver recovers them from ሀጠአ.
        """
        if not skeleton:
            return None

        norm = normalize_geez(get_consonant_skeleton(skeleton))
        candidates = self.skeleton_lookup.get(norm, [])
        if not candidates:
            grammar_pick = self.grammar.resolve_skeleton(
                skeleton, source=source, pattern_name=pattern_name
            )
            return grammar_pick
        if len(candidates) == 1:
            # A lone skeleton hit is not a citation unless C1 order agrees
            # (ልብ skeleton ለበ must not become ለበ).
            surface = source or stem
            if (
                surface
                and len(surface) < 3
                and not self._c1_compatible(candidates[0], surface)
            ):
                return None
            return candidates[0]

        # Exact surface / citation match wins among homophonous skeletons.
        if source in candidates:
            return source
        if stem in candidates:
            return stem

        if pattern_name in {"imperfective", "jussive"} and stem and get_char_order(stem[0]) == 6:
            for candidate in candidates:
                if self.lexicon_roots.get(candidate, {}).get("type") == "type_a":
                    return candidate

        order_surface = stem or source
        if order_surface:
            c1_order = get_char_order(order_surface[0])
            if c1_order:
                order_matches = [
                    candidate for candidate in candidates
                    if get_char_order(candidate[0]) == c1_order
                ]
                if order_matches:
                    candidates = self._prefer_citation_orthography(order_matches, order_surface)
                    if len(candidates) == 1:
                        return candidates[0]

        for candidate in candidates:
            if candidate in self.hollow_w_roots or candidate in self.hollow_y_roots:
                return candidate

        for candidate in candidates:
            root_type = self.lexicon_roots.get(candidate, {}).get("type", "")
            if root_type and root_type not in ("type_a", "strong", "unknown"):
                return candidate

        grammar_pick = self.grammar.resolve_skeleton(
            skeleton, source=source, pattern_name=pattern_name
        )
        if grammar_pick and grammar_pick in candidates:
            return grammar_pick

        # Prefer candidates that actually exist in the lexicon,
        # ranked toward the raw surface spelling.
        ranked = self._prefer_citation_orthography(
            [c for c in candidates if c in self.lexicon_roots] or list(candidates),
            stem or source,
        )
        return ranked[0] if ranked else None

    def _canonicalize_root(self, root, source=None, stem=None, pattern_name=None):
        """
        Resolve a derived root to lexicon canonical orthography.

        Internal normalization maps homophones (e.g. ሐ→ሀ) for matching, but
        user-facing output should use the lexicon citation form when known.
        """
        if not root:
            return root
        if root in self.lexicon_roots:
            return root

        norm = normalize_geez(root)
        if norm in self.lexicon_normalized_lookup:
            return self.lexicon_normalized_lookup[norm]

        canonical_w = self.hollow_w_lookup.get(norm)
        if canonical_w:
            return canonical_w

        canonical_y = self.hollow_y_lookup.get(norm)
        if canonical_y:
            return canonical_y

        citation = self._resolve_skeleton_citation(
            root, source=source, stem=stem, pattern_name=pattern_name
        )
        if citation:
            return citation

        grammar_pick = self.grammar.resolve_skeleton(
            root, source=source, pattern_name=pattern_name
        )
        if grammar_pick:
            return grammar_pick

        return root

    def _blocked_prefix_strip(self, word, prefix):
        """Prevent peeling verbal prefixes off integral root-initial clusters."""
        if prefix in {'አ', 'ም', 'መ'} and any(word.startswith(block) for block in self.prefix_block_starts):
            return True
        # Army-head template identity (አእመረ, ባረከ, …) is citation, not አ+stem.
        army = classify_army_head(word)
        if army and army.get("by") == "template_identity":
            return True
        # Bare triliteral/biliteral citations whose radicals equal prefix letters.
        if looks_like_verbal_citation(word) and len(word) <= 3:
            return True
        return False

    def _resolve_verbal_root(self, stem_or_root: str) -> tuple[str, str | None]:
        """Map a derived stem to its verbal ግስ root when known."""
        if stem_or_root in self.lexicon_roots:
            entry = self.lexicon_roots[stem_or_root]
            # Curated base_root annotation (2026-10-01 lexicon curation):
            # this entry is a derived stem kept for coverage; the analyzer
            # cannot strip it to its base, so map to the annotated base root.
            base = entry.get("base_root")
            if base:
                base_entry = self.lexicon_roots.get(base, {})
                return base, base_entry.get("meaning") or entry.get("meaning")
            return stem_or_root, entry.get("meaning")

        citation = self._canonicalize_root(stem_or_root, source=stem_or_root, stem=stem_or_root)
        if citation in self.lexicon_roots:
            return citation, self.lexicon_roots[citation].get("meaning")

        skel = normalize_geez(get_consonant_skeleton(stem_or_root))
        for candidate in self.skeleton_lookup.get(skel, []):
            if candidate in self.lexicon_roots:
                return candidate, self.lexicon_roots[candidate].get("meaning")

        grammar_pick = self.grammar.resolve_skeleton(stem_or_root, source=stem_or_root)
        if grammar_pick:
            gloss = self.grammar.primary_gloss(grammar_pick)
            return grammar_pick, gloss

        return stem_or_root, None

    def _try_noun_with_suffix(self, word, derivation_steps):
        """Match derived nominal forms with suffixes back to their verbal roots."""
        for noun_word in sorted(self.nouns.keys(), key=len, reverse=True):
            if not word.startswith(noun_word) or len(word) <= len(noun_word):
                continue
            suffix_part = word[len(noun_word):]
            if suffix_part not in self.suffixes:
                continue
            noun_entry = self.nouns[noun_word]
            verbal_root, verbal_gloss = self._resolve_verbal_root(
                noun_entry.get("root", noun_word)
            )
            skeleton = get_consonant_skeleton(verbal_root)
            derivation_steps.append({
                "step": len(derivation_steps) + 1,
                "action": "derived_noun_suffix",
                "description": "Derived nominal form with suffix → verbal root",
                "before": word,
                "after": verbal_root,
                "rule": (
                    f"ስምዕ '{noun_word}' ({noun_entry.get('meaning', 'Noun')}) "
                    f"+ suffix '{suffix_part}' → ግስ '{verbal_root}'"
                ),
            })
            return self._attach_classical_fields(
                {
                    "input": word,
                    "root": verbal_root,
                    "root_consonants": list(skeleton),
                    "root_type": "derived_noun",
                    "verb_home": detect_verb_home(skeleton, verbal_root),
                    "meaning": noun_entry.get("meaning") or verbal_gloss or verbal_root,
                    "confidence": 0.97,
                    "analysis": {
                        "stem": noun_word,
                        "pattern": {
                            "name": "derived_noun",
                            "geez_name": "ስምዕ",
                            "english_name": "Derived Noun",
                            "description": "Nominal form derived from a verbal root",
                        },
                        "prefixes": [],
                        "suffixes": [suffix_part],
                        "method": "derived_noun_suffix",
                        "surface_form": noun_word,
                        "verbal_gloss": verbal_gloss,
                    },
                    "derivation_path": derivation_steps,
                    "research_notation": {
                        "root_display": "{" + ", ".join(list(skeleton)) + "}",
                        "pattern_formula": f"ስምዕ({noun_word}) + Suffix({suffix_part})",
                        "affix_formula": f"Stem({noun_word}) + Suffix({suffix_part})",
                    },
                },
                in_nouns=True,
                noun_has_verbal_root=True,
            )
        return None

    def strip_affixes(self, word):
        """
        Recursively strips prefixes and suffixes with derivation tracking.
        
        Args:
            word: The input word.
            
        Returns:
            Tuple of (stripped_word, prefix_list, suffix_list, derivation_steps).
        """
        current_word = word
        found_prefixes = []
        found_suffixes = []
        derivation_steps = []
        
        changed = True
        while changed:
            changed = False

            # Feminine/nominal endings before asraw prefixes so ንግረት
            # peels ት (operator) rather than ን (false አሥራው).
            # Skip bare verbal citations (ሐተተ must not lose final ተ radical).
            if not looks_like_verbal_citation(current_word):
                for suffix in sorted(NOMINAL_FEMININE_ENDINGS, key=len, reverse=True):
                    if not current_word.endswith(suffix):
                        continue
                    remaining = current_word[: -len(suffix)]
                    remaining_skeleton = get_consonant_skeleton(remaining)
                    if len(remaining_skeleton) < 2:
                        continue
                    derivation_steps.append({
                        "action": "strip_suffix",
                        "affix": suffix,
                        "before": current_word,
                        "after": remaining,
                        "rule": (
                            f"Feminine/nominal ending '{suffix}' stripped "
                            f"(fere_geez.ch4.tire_zer.feminine_ending; "
                            f"ት/ታ are ending orders, not radicals)"
                        ),
                    })
                    found_suffixes.append(suffix)
                    current_word = remaining
                    changed = True
                    break
            if changed:
                continue
            
            had_feminine = any(
                s in NOMINAL_FEMININE_ENDINGS for s in found_suffixes
            )
            for prefix in self.prefixes:
                if current_word.startswith(prefix):
                    if self._blocked_prefix_strip(current_word, prefix):
                        continue
                    # After feminine ending: block false asraw peels on nouns,
                    # but allow causative A and agentive ma+geminate stems.
                    if had_feminine:
                        if prefix in {'ን', 'ይ', 'ት', 'እ', 'ና', 'ያ', 'ታ', 'ላ'}:
                            continue
                        if prefix == 'መ':
                            rem = current_word[len(prefix):]
                            rem_orders = [get_char_order(c) for c in rem]
                            geminate_stem = (
                                len(rem) >= 3
                                and rem_orders[0] != 6
                                and rem_orders[-1] == 6
                                and rem_orders[-2] == 6
                            )
                            if not geminate_stem:
                                continue
                    remaining = current_word[len(prefix):]
                    remaining_skeleton = get_consonant_skeleton(remaining)
                    
                    if prefix == 'መ':
                        if current_word in self.nouns:
                            continue
                        # All-Ge'ez quadriliteral (መነገነ): መ is C1, not mä-.
                        if (
                            len(current_word) == 4
                            and all(get_char_order(c) == 1 for c in current_word)
                        ):
                            continue

                        if len(remaining) > 0:
                            last_char = remaining[-1]
                            if get_char_order(last_char) == 1 and len(remaining_skeleton) >= 3:
                                skeleton_full = get_consonant_skeleton(current_word)
                                if skeleton_full in self.quadriliterals:
                                    continue

                    # አስተ/ታስተ stay intact even when the remainder is only
                    # two radicals (አስተማረ). A shorter prefix must not eat them.
                    stem4_prefix = prefix in {
                        "ያስተ", "ታስተ", "ናስተ", "ላስተ", "መስተ", "አስተ",
                    }
                    min_skeleton = 2 if stem4_prefix else 3
                    if len(remaining_skeleton) >= min_skeleton and remaining:
                        derivation_steps.append({
                            "action": "strip_prefix",
                            "affix": prefix,
                            "before": current_word,
                            "after": remaining,
                            "rule": f"Prefix '{prefix}' stripped (skeleton >= 3)"
                        })
                        found_prefixes.append(prefix)
                        current_word = remaining
                        changed = True
                        break
                    elif len(remaining_skeleton) == 2 and (
                        self._is_weak_root_candidate(remaining)
                        or self._is_laryngeal_drop_candidate(remaining)
                    ):
                        # Do not strip ወ when it is the weak-initial radical:
                        # if 'ወ' + skeleton(remaining) is a known weak-initial
                        # root, the ወ belongs to the root (e.g. ወርዱ <- ወረደ).
                        if prefix == "ወ" and self._is_weak_root_candidate(remaining):
                            continue
                        # Do not peel the first letter off a complete triliteral
                        # zend/kalay stem (ንግር, ከትም). Exception: asraw ይ/ት/እ
                        # before bihla drop (ይብል looks like [6,6,6] but ይ is asraw).
                        cur_orders = [get_char_order(c) for c in current_word]
                        if len(current_word) == 3 and tuple(cur_orders) in {
                            (6, 6, 6), (1, 6, 6)
                        }:
                            if not (
                                prefix in {"ይ", "ት", "እ"}
                                and self._is_laryngeal_drop_candidate(remaining)
                            ):
                                continue
                        # Laryngeal-drop peel is only valid for asraw letters.
                        asraw_forms = {"ይ", "ት", "እ", "ን"}
                        if (
                            self._is_laryngeal_drop_candidate(remaining)
                            and not self._is_weak_root_candidate(remaining)
                            and prefix not in asraw_forms
                        ):
                            continue
                        why = (
                            "laryngeal-drop candidate"
                            if self._is_laryngeal_drop_candidate(remaining)
                            else "weak root candidate"
                        )
                        derivation_steps.append({
                            "action": "strip_prefix",
                            "affix": prefix,
                            "before": current_word,
                            "after": remaining,
                            "rule": f"Prefix '{prefix}' stripped ({why})"
                        })
                        found_prefixes.append(prefix)
                        current_word = remaining
                        changed = True
                        break
            
            if changed:
                continue

            for suffix in self.suffixes:
                if current_word.endswith(suffix):
                    if suffix in NOMINAL_FEMININE_ENDINGS:
                        # Already handled above (priority pass).
                        continue
                    remaining = current_word[:-len(suffix)]
                    remaining_skeleton = get_consonant_skeleton(remaining)
                    
                    if len(remaining_skeleton) >= 3:
                        if not suffix_strip_allowed(suffix, prefixes=found_prefixes, remaining=remaining, current_word=current_word):
                            continue
                        rule = f"Suffix '{suffix}' stripped (skeleton >= 3)"
                        derivation_steps.append({
                            "action": "strip_suffix",
                            "affix": suffix,
                            "before": current_word,
                            "after": remaining,
                            "rule": rule,
                        })
                        found_suffixes.append(suffix)
                        current_word = remaining
                        changed = True
                        break
                    elif len(remaining_skeleton) == 2:
                        if not suffix_strip_allowed(suffix, prefixes=found_prefixes, remaining=remaining, current_word=current_word):
                            continue
                        # Check for weak root or laryngeal middle
                        is_reconstructable = self._is_weak_root_candidate(remaining)
                        if not is_reconstructable:
                            # Check for laryngeal middle candidate
                            laryngeal_root, _ = self._reconstruct_laryngeal_middle(remaining_skeleton)
                            is_reconstructable = laryngeal_root is not None
                        
                        if is_reconstructable:
                            derivation_steps.append({
                                "action": "strip_suffix",
                                "affix": suffix,
                                "before": current_word,
                                "after": remaining,
                                "rule": f"Suffix '{suffix}' stripped (reconstructable root candidate)"
                            })
                            found_suffixes.append(suffix)
                            current_word = remaining
                            changed = True
                            break
        
        return current_word, found_prefixes, found_suffixes, derivation_steps

    def identify_verb_pattern(self, stem, prefixes, suffixes=None):
        """
        Identifies the grammatical pattern (Anqets/binyan) and stem number.
        
        Detects 5 verb stems and their tenses:
        - Stem IV (አስተሳሳቢ): ያስተ-, ታስተ-, ናስተ-, አስተ- prefixes
        - Stem III (አሳሳቢ): ያ-, ታ-, ና-, አ- prefixes
        - Stem II (ተገብሮ): ይት-, ትت-, ተ- prefixes
        - Stem I (ቀዳማይ): Basic ይ-, ት-, እ-, ን- or no prefix
        
        Args:
            stem: The verb stem.
            prefixes: List of prefixes found.
            
        Returns:
            Pattern info dict with geez name, stem number, and description.
        """
        skeleton = get_consonant_skeleton(stem)
        suffixes = suffixes or []

        # Feminine/nominal ending => tire zer / sim'e, not a verbal anqets.
        if any(s in NOMINAL_FEMININE_ENDINGS for s in suffixes):
            return {
                "name": "derived_noun",
                "geez_name": "ጥሬ ዘር / ስምዕ",
                "english_name": "Derived Noun",
                "stem_number": 0,
                "description": "Nominal form with feminine/noun ending",
            }

        # =================================================================
        # STEM IV: Causative-Passive (አስተሳሳቢ) - Check first (longest)
        # =================================================================
        stem4_imperf = ['ያስተ', 'ታስተ', 'ናስተ']
        stem4_juss = ['ላስተ']
        stem4_perf = ['አስተ', 'መስተ']
        
        if any(p in stem4_imperf for p in prefixes):
            return {
                "name": "causative_passive_imperfective",
                "geez_name": "አስተሳሳቢ ካልኣይ",
                "english_name": "Causative-Passive Imperfective",
                "stem_number": 4,
                "description": "Stem IV: Causative-passive ongoing action"
            }
        if any(p in stem4_juss for p in prefixes):
            return {
                "name": "causative_passive_jussive",
                "geez_name": "አስተሳሳቢ ሣልሳይ",
                "english_name": "Causative-Passive Jussive",
                "stem_number": 4,
                "description": "Stem IV: Causative-passive wish/command"
            }
        if any(p in stem4_perf for p in prefixes):
            return {
                "name": "causative_passive_perfective",
                "geez_name": "አስተሳሳቢ ቀዳማይ",
                "english_name": "Causative-Passive Perfective",
                "stem_number": 4,
                "description": "Stem IV: Causative-passive completed action"
            }
        
        # =================================================================
        # STEM III: Causative (አሳሳቢ) - includes አስ- verbs
        # =================================================================
        stem3_imperf = ['ያ', 'ታ', 'ና', 'ያስ', 'ታስ', 'ናስ']
        stem3_juss = ['ላስ']
        
        if any(p in stem3_imperf for p in prefixes):
            return {
                "name": "causative_imperfective",
                "geez_name": "አሳሳቢ ካልኣይ",
                "english_name": "Causative Imperfective",
                "stem_number": 3,
                "description": "Stem III: Causing action (ongoing)"
            }
        
        if any(p in stem3_juss for p in prefixes):
            return {
                "name": "causative_jussive",
                "geez_name": "አሳሳቢ ሣልሳይ",
                "english_name": "Causative Jussive",
                "stem_number": 3,
                "description": "Stem III: Causing action (wish/command)"
            }
        
        if 'አ' in prefixes and len(prefixes) == 1:
            return {
                "name": "causative_perfective",
                "geez_name": "አሳሳቢ ቀዳማይ",
                "english_name": "Causative Perfective",
                "stem_number": 3,
                "description": "Stem III: Causing action (completed)"
            }
        
        if 'አስ' in prefixes and len(prefixes) == 1:
            return {
                "name": "causative_perfective",
                "geez_name": "አሳሳቢ ቀዳማይ",
                "english_name": "Causative Perfective (አስ-verb)",
                "stem_number": 3,
                "description": "Stem III: Causing action (completed)"
            }
        
        # =================================================================
        # STEM II: Passive/Reflexive (ተገብሮ)
        # =================================================================
        stem2_imperf = ['ይት', 'ትת', 'እת', 'ንת']
        
        if any(p in stem2_imperf for p in prefixes):
            return {
                "name": "passive_imperfective",
                "geez_name": "ተገብሮ ካልኣይ",
                "english_name": "Passive Imperfective",
                "stem_number": 2,
                "description": "Stem II: Passive/reflexive ongoing action"
            }
        
        if 'ተ' in prefixes and not any(p in ['ያ', 'ታ', 'ና', 'አስተ'] for p in prefixes):
            return {
                "name": "passive_perfective",
                "geez_name": "ተገብሮ ቀዳማይ",
                "english_name": "Passive Perfective",
                "stem_number": 2,
                "description": "Stem II: Passive/reflexive completed action"
            }
        
        # =================================================================
        # STEM I: Basic (ቀዳማይ ግንድ)
        # =================================================================
        imperfect_prefixes = ['ይ', 'ት', 'እ', 'ን']
        if any(p in imperfect_prefixes for p in prefixes):
            return {
                "name": "imperfective",
                "geez_name": "ካልዓይ / ትንቢት አንቀጽ",
                "english_name": "Imperfective",
                "stem_number": 1,
                "description": "Stem I: Basic ongoing/habitual action (ፍሬ ግእዝ አንቀጽ)",
            }
        
        # Imperative: C1 is 6th order (Sādis)
        if len(stem) >= 2 and get_char_order(stem[0]) == 6:
            return {
                "name": "imperative",
                "geez_name": "ትእዛዝ",
                "english_name": "Imperative",
                "stem_number": 1,
                "description": "Stem I: Direct command"
            }
        
        # Perfective: citation form ends in Ge'ez order (ፍሬ ግእዝ §4.2)
        if len(skeleton) >= 3 and len(stem) > 0 and get_char_order(stem[-1]) == 1:
            return {
                "name": "perfective",
                "geez_name": "ኃላፊ / ቀዳማይ አንቀጽ",
                "english_name": "Perfective",
                "stem_number": 1,
                "description": "Stem I: Basic completed action (ፍሬ ግእዝ ኃላፊ)",
            }
            
        return {
            "name": "unknown",
            "geez_name": "ያልታወቀ",
            "english_name": "Unknown/Noun",
            "stem_number": 0,
            "description": "Pattern could not be determined"
        }

    def _get_root_type(self, root):
        """Determine the morphological type of a root."""
        if root in self.lexicon_roots:
            return self.lexicon_roots[root].get('type', 'unknown')
        
        if len(root) == 4:
            return "quadriliteral"
        
        if len(root) >= 2:
            c2 = devowelize(root[1]) if len(root) > 1 else ''
            if c2 == 'ወ':
                return "hollow_w"
            elif c2 == 'የ':
                return "hollow_y"
        
        if len(root) >= 1 and devowelize(root[0]) == 'ወ':
            return "weak_initial"
        
        return "strong"

    def extract_root(self, word):
        """
        Extract the root from a Ge'ez word with full research metadata.
        
        Args:
            word: The input word.
            
        Returns:
            Complete analysis dict with derivation path.
        """
        derivation_steps = []
        
        normalized = normalize_geez(word)
        if word != normalized:
            derivation_steps.append({
                "step": 1,
                "action": "normalize",
                "description": "Homophone normalization",
                "before": word,
                "after": normalized,
                "rule": "Map phonetic variants to canonical forms"
            })

        # Non-lexical input: no Ethiopic syllable letters (punctuation, digits,
        # Latin, ...). Ethiopic letters are U+1200-U+135F; U+1360-U+137F is
        # punctuation and numerals. Must not be assigned a root; these pollute
        # the root inventory.
        if not any('\u1200' <= c <= '\u135F' for c in normalized):
            derivation_steps.append({
                "step": len(derivation_steps) + 1,
                "action": "non_lexical",
                "description": "Input has no Ethiopic letters; not a valid root",
                "before": word,
                "after": normalized,
                "rule": "Non-lexical tokens (punctuation, digits, foreign script) are rejected, not rooted",
            })
            return {
                "input": word,
                "root": None,
                "root_consonants": [],
                "root_type": "non_lexical",
                "verb_home": None,
                "meaning": None,
                "confidence": 1.0,
                "word_class": "non_lexical",
                "word_class_geez": "ያልሆነ",
                "analysis": {
                    "stem": normalized,
                    "pattern": {"name": "non_lexical", "english_name": "Non-lexical token"},
                    "prefixes": [],
                    "suffixes": [],
                    "method": "non_lexical",
                },
                "derivation_path": derivation_steps,
                "research_notation": {
                    "root_display": "{}",
                    "pattern_formula": "NonLexical",
                    "affix_formula": "ø",
                },
            }

        particle_segments = self._segment_particles(normalized)
        if particle_segments:
            return self._build_particle_result(word, particle_segments, derivation_steps)

        if len(normalized) == 1:
            one_char_map = {
                'ፃ': ('ወጸአ', "Imperative of ወጸአ 'to go out'"),
                'ጻ': ('ወጸአ', "Imperative of ወጸአ 'to go out'"),
                'ሖ': ('ሐወረ', "Imperative of ሐወረ 'to go'"),
                'ሆ': ('ሐወረ', "Imperative of ሐወረ 'to go'")
            }
            if normalized in one_char_map:
                root, explanation = one_char_map[normalized]
                derivation_steps.append({
                    "step": 2,
                    "action": "one_char_lookup",
                    "description": "Single-character imperative reconstruction",
                    "before": normalized,
                    "after": root,
                    "rule": explanation
                })
                return self._build_result(word, root, normalized, [], [], derivation_steps, "irregular")

        # Zewadla labels on the raw spelling, before homophone normalization
        # collapses ሠርሐቀደ onto the type-A twin ሰርሐ.
        code_hit = self._match_pattern_code_label(word)
        if code_hit:
            base, code, pattern_info = code_hit
            if base in self.lexicon_roots or base in self.lexicon_normalized_lookup:
                # Prefer the raw lexicon key over its normalized twin.
                if base not in self.lexicon_roots:
                    base = self.lexicon_normalized_lookup.get(normalize_geez(base), base)
                derivation_steps.append({
                    "step": len(derivation_steps) + 1,
                    "action": "pattern_code_label",
                    "description": "Dictionary label: citation + Zewadla pattern code",
                    "before": word,
                    "after": base,
                    "rule": (
                        f"Pattern code '{code}' ({pattern_info['english_name']}); "
                        f"base '{base}' kept from the raw spelling"
                    ),
                })
                return self._build_result(
                    word, base, base, [], [code], derivation_steps, "pattern_code",
                    pattern_override={
                        "name": pattern_info["name"],
                        "geez_name": pattern_info["geez_name"],
                        "english_name": pattern_info["english_name"],
                        "stem_number": 1,
                        "description": f"Zewadla pattern code '{code}'",
                    },
                )

        if is_merahiyan(word) or is_merahiyan(normalized):
            return self._build_nonverbal(word, word, "pronoun", derivation_steps)
        if (
            self.lexicon_roots
            and word not in self.lexicon_roots
            and normalized not in self.lexicon_roots
            and (word in CITATION_NOUNS or normalized in CITATION_NOUNS)
        ):
            return self._build_nonverbal(word, word, "noun", derivation_steps)

        skeleton_initial = get_consonant_skeleton(normalized)
        order_signal = get_char_order(normalized[0]) if normalized else 0
        has_order_signal = order_signal in [3, 5, 7]

        if len(skeleton_initial) == 2 and not has_order_signal:
            hollow_root, hollow_type = self._try_hollow_middle_restore(skeleton_initial)
            if hollow_root:
                action = (
                    "reconstruct_hollow_w_lexicon"
                    if hollow_type == "hollow_w"
                    else "reconstruct_hollow_y_lexicon"
                )
                radical = "ወ" if hollow_type == "hollow_w" else "የ"
                derivation_steps.append({
                    "step": 2,
                    "action": action,
                    "description": f"Reconstruct hollow-{radical} middle radical",
                    "before": normalized,
                    "after": hollow_root,
                    "rule": f"2-letter stem matches known {hollow_type} root. Restored {radical} as C2."
                })
                return self._build_result(
                    word, hollow_root, normalized, [], [], derivation_steps, "derived"
                )

        if normalized in self.nouns:
            noun_entry = self.nouns[normalized]
            verbal_root, verbal_gloss = self._resolve_verbal_root(
                noun_entry.get("root", normalized)
            )
            root_type = "derived_noun" if noun_entry.get("root") else "noun"
            skeleton = get_consonant_skeleton(verbal_root)
            verb_home = detect_verb_home(skeleton, verbal_root)
            
            return self._attach_classical_fields(
                {
                    "input": word,
                    "root": verbal_root,
                    "root_consonants": list(skeleton),
                    "root_type": root_type,
                    "verb_home": verb_home,
                    "meaning": noun_entry.get("meaning", verbal_gloss or "Noun"),
                    "confidence": 1.0,
                    "analysis": {
                        "stem": normalized,
                        "pattern": {
                            "name": "derived_noun" if root_type == "derived_noun" else "noun",
                            "geez_name": "ስምዕ" if root_type == "derived_noun" else "ስም",
                            "english_name": "Derived Noun" if root_type == "derived_noun" else "Noun",
                            "description": (
                                "Nominal form derived from verbal root"
                                if root_type == "derived_noun"
                                else "Protected Noun"
                            ),
                        },
                        "prefixes": [],
                        "suffixes": [],
                        "method": "lexicon_noun",
                        "surface_form": normalized,
                        "verbal_gloss": verbal_gloss,
                    },
                    "derivation_path": [{
                        "step": len(derivation_steps) + 1,
                        "action": "noun_match",
                        "description": "Derived nominal → verbal root",
                        "before": normalized,
                        "after": verbal_root,
                        "rule": f"ስምዕ '{normalized}' → ግስ '{verbal_root}' ({verbal_gloss or 'N/A'})",
                    }],
                    "research_notation": {
                        "root_display": "{" + ", ".join(list(skeleton)) + "}",
                        "pattern_formula": "ስምዕ" if root_type == "derived_noun" else "Noun",
                        "affix_formula": "Stem",
                    },
                },
                in_nouns=True,
                noun_has_verbal_root=bool(noun_entry.get("root")),
            )

        noun_suffix_result = self._try_noun_with_suffix(normalized, derivation_steps)
        if noun_suffix_result:
            noun_suffix_result["input"] = word
            return noun_suffix_result

        # Math-first: no lexicon-first shortcuts. The old citation_hit and
        # skeleton-citation blocks returned method="lexicon" here, skipping
        # the order/base/revowelize math entirely. Every form now flows
        # through strip_affixes + restore_citation_root below; the lexicon
        # only annotates gloss and verb type afterwards in _build_result.
        # (Raw homophones like ሠርሐ are preserved because the math operates
        # on the raw character bases, not normalized forms.)

        # Weak-initial imperfective/jussive: ይ/ት/እ + 2-char stem where
        # 'ወ' + stem skeleton is a known weak-initial root (e.g. ይሃብ ->
        # ወሀበ). Must precede the PDF bihla path, which would otherwise
        # claim the whole form as a bihla-house stem (ይህበ).
        weak_imp = self._try_weak_initial_imperfective(normalized)
        if weak_imp:
            root_w, pref_w = weak_imp
            derivation_steps.append({
                "step": len(derivation_steps) + 1,
                "action": "strip_prefix",
                "affix": pref_w,
                "before": normalized,
                "after": normalized[len(pref_w):],
                "rule": "Imperfective/jussive prefix stripped; weak-initial ወ restored",
            })
            return self._build_result(
                word,
                root_w,
                normalized[len(pref_w):],
                [pref_w],
                [],
                derivation_steps,
                "weak_initial_imperfective",
            )

        pdf_hit = analyze_surface_pdf(normalized)
        if pdf_hit:
            derivation_steps.append({
                "step": len(derivation_steps) + 1,
                "action": "pdf_anqets_analysis",
                "description": "fere_geez asraw/anqets table path",
                "before": normalized,
                "after": pdf_hit["citation"],
                "rule": f"{pdf_hit['source_rule']} ({pdf_hit['by']})",
            })
            for pref in pdf_hit.get("prefixes") or []:
                derivation_steps.append({
                    "step": len(derivation_steps) + 1,
                    "action": "strip_prefix",
                    "affix": pref,
                    "before": normalized,
                    "after": pdf_hit["stem"],
                    "rule": f"asraw '{pref}' (fere_geez.ch4.asraw)",
                })
            return self._build_result(
                word,
                pdf_hit["citation"],
                pdf_hit["stem"],
                pdf_hit.get("prefixes") or [],
                pdf_hit.get("suffixes") or [],
                derivation_steps,
                "pdf_anqets",
            )

        # Zewadla pattern-code dictionary labels (e.g. ሰርሐቀተ = ሰርሐ + ቀተ).
        # Must precede affix stripping so ተ is not peeled as a feminine ending.
        code_hit = self._match_pattern_code_label(normalized)
        if code_hit:
            base, code, pattern_info = code_hit
            derivation_steps.append({
                "step": len(derivation_steps) + 1,
                "action": "pattern_code_label",
                "description": "Dictionary label: citation + Zewadla pattern code",
                "before": normalized,
                "after": base,
                "rule": (
                    f"Pattern code '{code}' ({pattern_info['english_name']}); "
                    f"base '{base}' is a lexicon root or valid citation shape"
                ),
            })
            return self._build_result(
                word, base, base, [], [code], derivation_steps, "pattern_code",
                pattern_override={
                    "name": pattern_info["name"],
                    "geez_name": pattern_info["geez_name"],
                    "english_name": pattern_info["english_name"],
                    "stem_number": 1,
                    "description": f"Zewadla pattern code '{code}'",
                },
            )

        # Math-first: strip affixes from the RAW word, not the normalized form.
        # normalize_geez collapses homophones (ሠ→ሰ, ሐ→ሀ), which would lose
        # the raw spelling that the math must preserve (Bug 2: ሠርሐ stays
        # ሠርሐ). The order/base/revowelize math operates correctly on raw
        # characters; devowelize(ሠ)=ሠ, not ሰ.
        stem, prefixes, suffixes, affix_steps = self.strip_affixes(word)
        for i, step in enumerate(affix_steps):
            step["step"] = len(derivation_steps) + 1 + i
            derivation_steps.append(step)

        # Rule-first citation restore (applies to every stem, not selected lemmas).
        restored = restore_citation_root(stem)
        root = restored["citation"]
        derivation_steps.append({
            "step": len(derivation_steps) + 1,
            "action": "restore_citation_root",
            "description": "Order-math citation restore",
            "before": stem,
            "after": root,
            "rule": f"{restored['source_rule']} ({restored['by']})",
        })

        # Grammar index is corroboration only, never invent a mismatched root.
        grammar_roots = [
            g for g in self.grammar.lookup_form(normalized)
            if grammar_root_compatible(stem or normalized, g)
        ]
        if not grammar_roots and stem != normalized:
            grammar_roots = [
                g for g in self.grammar.lookup_form(stem)
                if grammar_root_compatible(stem, g)
            ]
        # Prefer rule citation when it already satisfies paper constraints;
        # only fall through to grammar when restore was weak (empty stem)
        # and grammar offers a compatible hit.
        if (
            grammar_roots
            and restored["by"] in {"empty"}
        ):
            root = grammar_roots[0]
            derivation_steps.append({
                "step": len(derivation_steps) + 1,
                "action": "grammar_form_lookup",
                "description": "Compatible grammar corroboration",
                "before": stem,
                "after": root,
                "rule": f"Grammar maps form to compatible root '{root}'",
            })
            return self._build_result(
                word, root, stem, prefixes, suffixes, derivation_steps, "grammar_form"
            )

        skeleton = get_consonant_skeleton(stem)
        
        if len(root) == 2 and len(stem) >= 1:
            first_char_stem = stem[0]
            order = get_char_order(first_char_stem)
            
            if order == 7:
                reconstructed = root[0] + 'ወ' + root[1]
                derivation_steps.append({
                    "step": len(derivation_steps) + 1,
                    "action": "reconstruct_hollow_w",
                    "description": "Reconstruct hollow-W middle radical",
                    "before": root,
                    "after": reconstructed,
                    "rule": f"7th order vowel (O) on C1 indicates hidden ወ. Pattern: C1o = C1+ወ+C2"
                })
                root = reconstructed
            elif order in [3, 5]:
                reconstructed = root[0] + 'የ' + root[1]
                derivation_steps.append({
                    "step": len(derivation_steps) + 1,
                    "action": "reconstruct_hollow_y",
                    "description": "Reconstruct hollow-Y middle radical",
                    "before": root,
                    "after": reconstructed,
                    "rule": f"3rd/5th order vowel (I/E) on C1 indicates hidden የ. Pattern: C1i/e = C1+የ+C2"
                })
                root = reconstructed
            else:
                # Try laryngeal middle reconstruction (C2 dropped in Jussive/Imperative)
                laryngeal_root, laryngeal_char = self._reconstruct_laryngeal_middle(root)
                if laryngeal_root:
                    derivation_steps.append({
                        "step": len(derivation_steps) + 1,
                        "action": "reconstruct_laryngeal_middle",
                        "description": "Reconstruct laryngeal middle radical",
                        "before": root,
                        "after": laryngeal_root,
                        "rule": f"2-letter stem with missing C2. Laryngeal '{laryngeal_char}' reconstructed. Pattern: C1+{laryngeal_char}+C3 (ላሪንጅያል መካከል)"
                    })
                    root = laryngeal_root
                
        if len(root) == 2:
            hollow_root, hollow_type = self._try_hollow_middle_restore(root)
            if hollow_root:
                action = (
                    "reconstruct_hollow_w_lexicon"
                    if hollow_type == "hollow_w"
                    else "reconstruct_hollow_y_lexicon"
                )
                radical = "ወ" if hollow_type == "hollow_w" else "የ"
                derivation_steps.append({
                    "step": len(derivation_steps) + 1,
                    "action": action,
                    "description": f"Reconstruct hollow-{radical} middle radical",
                    "before": root,
                    "after": hollow_root,
                    "rule": f"2-letter stem matches known {hollow_type} root. Restored {radical} as C2."
                })
                root = hollow_root
            else:
                laryngeal_root, laryngeal_char = self._reconstruct_laryngeal_middle(root)
                if laryngeal_root:
                    derivation_steps.append({
                        "step": len(derivation_steps) + 1,
                        "action": "reconstruct_laryngeal_middle",
                        "description": "Reconstruct laryngeal middle radical",
                        "before": root,
                        "after": laryngeal_root,
                        "rule": f"2-letter stem matches laryngeal-middle pattern. Restored '{laryngeal_char}' as C2."
                    })
                    root = laryngeal_root
                else:
                    candidate = 'ወ' + root
                    if candidate in self.weak_initial_roots:
                        derivation_steps.append({
                            "step": len(derivation_steps) + 1,
                            "action": "reconstruct_weak_initial",
                            "description": "Reconstruct assimilated initial ወ",
                            "before": root,
                            "after": candidate,
                            "rule": "2-letter stem matches weak-initial pattern. Restored ወ prefix."
                        })
                        root = candidate

        nonverbal = (
            restored.get("by") == "keep_surface_nonverbal"
            and not prefixes
            and not suffixes
        )
        if nonverbal and root not in self.lexicon_roots:
            return self._build_result(
                word, root, stem, prefixes, suffixes, derivation_steps, "order_math",
                pattern_override={
                    "name": "unknown",
                    "geez_name": "ያልታወቀ",
                    "english_name": "Unknown/Noun",
                    "stem_number": 0,
                    "description": "Order math found no verb pattern",
                },
            )
        return self._build_result(word, root, stem, prefixes, suffixes, derivation_steps, "order_math")

    def _build_nonverbal(self, word, root, kind, derivation_steps):
        """Closed-class pronoun or citation noun: not a pdf_anqets verb."""
        is_noun = kind == "noun"
        pattern = {
            "name": "noun" if is_noun else "particle_phrase",
            "geez_name": "ስም" if is_noun else "መራሕያን",
            "english_name": "Noun" if is_noun else "Pronoun",
            "stem_number": 0,
            "description": "Closed class; not a verb root",
        }
        derivation_steps = list(derivation_steps or [])
        derivation_steps.append({
            "step": len(derivation_steps) + 1,
            "action": "closed_class",
            "description": "Pronoun or citation noun blocked from verbal analysis",
            "before": word,
            "after": root,
            "rule": (
                "Closed-class form is not a verb root; "
                "pdf_anqets and skeleton verb citations are suppressed"
            ),
        })
        result = {
            "input": word,
            "root": root,
            "root_consonants": list(get_consonant_skeleton(root)),
            "root_type": "noun" if is_noun else "merahiyan",
            "verb_home": None,
            "meaning": None,
            "confidence": 1.0,
            "analysis": {
                "stem": root,
                "pattern": pattern,
                "prefixes": [],
                "suffixes": [],
                "method": "closed_class",
            },
            "derivation_path": derivation_steps,
            "research_notation": {
                "root_display": "{" + ", ".join(list(root)) + "}",
                "pattern_formula": "Noun" if is_noun else "Merahiyan",
                "affix_formula": "ø",
            },
        }
        return self._attach_classical_fields(
            result,
            in_nouns=is_noun,
            noun_has_verbal_root=False,
        )

    def _attach_classical_fields(
        self,
        result,
        *,
        in_nouns=False,
        noun_has_verbal_root=False,
    ):
        """Attach additive classical Sawasow fields (root class / anqets / army head)."""
        analysis = result.get("analysis") or {}
        classical = build_classical_analysis(
            root=result.get("root") or "",
            stem=analysis.get("stem") or result.get("root") or "",
            prefixes=analysis.get("prefixes") or [],
            suffixes=analysis.get("suffixes") or [],
            pattern=analysis.get("pattern"),
            root_type=result.get("root_type"),
            method=analysis.get("method"),
            in_lexicon_verbs=(result.get("root") or "") in self.lexicon_roots,
            in_nouns=in_nouns,
            noun_has_verbal_root=noun_has_verbal_root,
            surface=analysis.get("stem") or result.get("input") or "",
        )
        result["word_class"] = classical["word_class"]
        result["word_class_geez"] = classical["word_class_geez"]
        result["root_class"] = classical["root_class"]
        result["root_class_geez"] = classical["root_class_geez"]
        result["army_head"] = classical["army_head"]
        result["anqets"] = classical["anqets"]
        result["asraw_markers"] = classical["asraw_markers"]
        result["anqets_transforms"] = classical.get("anqets_transforms")
        result["arist_transforms"] = classical.get("arist_transforms")
        result["balabet_suffix"] = classical.get("balabet_suffix")
        result["structural_features"] = classical.get("structural_features")
        result["citation_constraints"] = classical["citation_constraints"]
        result["source_rule"] = classical["source_rule"]
        result["source_rules"] = classical["source_rules"]
        analysis["classical"] = {
            "word_class": classical["word_class"],
            "army_head_info": classical["army_head_info"],
            "anqets": classical["anqets"],
            "asraw_markers": classical["asraw_markers"],
            "balabet_suffix": classical.get("balabet_suffix"),
        }
        result["analysis"] = analysis
        return result

    def _build_result(self, word, root, stem, prefixes, suffixes, derivation_steps, method, pattern_override=None):
        """
        Build the standardized result dictionary with algorithmic verb type detection.
        
        Includes the 'verb_home' field which algorithmically detects the verb class
        based on radical count and vowel quality (C1 order), without requiring 
        lexicon lookup. Also detects causative prefixes.

        pattern_override: explicit pattern dict (e.g. from a Zewadla pattern-code
        label) that bypasses identify_verb_pattern inference.
        """
        if pattern_override is not None:
            pattern = pattern_override
        else:
            pattern = self.identify_verb_pattern(stem, prefixes, suffixes)
        # Math-first: the root derived by restore_citation_root (order/base/
        # revowelize) is final. The lexicon must not decide the root; it only
        # attaches gloss and verb type afterwards (see lexicon_entry below).
        # The old _canonicalize_root override (skeleton citation lookup,
        # homophone-normalized mapping) is removed: it let the dictionary
        # pick the root, skipping the math.

        root_type = self._get_root_type(root)
        if (
            pattern_override is not None
            and pattern_override.get("name") == "unknown"
            and root not in self.lexicon_roots
        ):
            root_type = "unknown"
        
        # Post-hoc lexicon annotation: gloss and verb type only.
        lexicon_entry = self.lexicon_roots.get(root, {})
        meaning = lexicon_entry.get('meaning', None)
        lexicon_verb_type = lexicon_entry.get('type', None)
        if method == "pattern_code":
            grammar_gloss = self.grammar.primary_gloss(root)
            if grammar_gloss:
                meaning = grammar_gloss
        if not meaning:
            meaning = self.grammar.primary_gloss(root)

        grammar_ref = self.grammar.reference(root)
        grammar_patterns = self.grammar.grammar_patterns(root)
        
        # Classify from the citation, not the inflected surface.
        # If the lexicon disagrees, keep the lexicon class.
        verb_home = detect_verb_home(get_consonant_skeleton(root), root)
        detected_type = verb_home.get("type")
        if lexicon_verb_type and lexicon_verb_type != "unknown":
            verb_home = dict(verb_home)
            verb_home["type"] = lexicon_verb_type
            verb_home["detected_type"] = detected_type
            verb_home["lexicon_type"] = lexicon_verb_type
            if detected_type != lexicon_verb_type:
                verb_home["evidence"] = (
                    f"Lexicon class {lexicon_verb_type} kept; "
                    f"citation detect was {detected_type}"
                )
        
        # Detect causative prefix (ያ, ታ, ና, አ)
        is_causative = any(p in self.causative_prefixes for p in prefixes)
        if is_causative:
            verb_home['features']['is_causative'] = True
            verb_home['features']['causative_prefix'] = [p for p in prefixes if p in self.causative_prefixes][0]
        
        derivation_steps.append({
            "step": len(derivation_steps) + 1,
            "action": "detect_verb_home",
            "description": "Algorithmic verb class detection",
            "before": f"skeleton={root}, stem={stem}",
            "after": verb_home['type'],
            "rule": verb_home['evidence']
        })
        if lexicon_verb_type:
            derivation_steps.append({
                "step": len(derivation_steps) + 1,
                "action": "lexicon_type_annotation",
                "description": "Lexicon verb type attached after math derivation",
                "before": verb_home['type'],
                "after": lexicon_verb_type,
                "rule": "Lexicon annotates type; it does not decide the root"
            })

        # Confidence reflects math derivation, not lexicon hits.
        # method="lexicon" no longer occurs (it meant the math was skipped).
        has_gloss = bool(meaning)
        if method in ("derived", "order_math", "pattern_code", "grammar_form"):
            confidence = 0.90 if has_gloss else 0.85
        else:
            confidence = 0.70

        result = {
            "input": word,
            "root": root,
            "root_consonants": list(get_consonant_skeleton(root)),
            "root_type": root_type,
            "verb_home": verb_home,
            "meaning": meaning,
            "confidence": confidence,
            "analysis": {
                "stem": stem,
                "pattern": pattern,
                "prefixes": prefixes,
                "suffixes": suffixes,
                "method": method,
                "is_causative": is_causative,
                "grammar_ref": grammar_ref,
                "grammar_patterns": grammar_patterns,
            },
            "derivation_path": derivation_steps,
            "research_notation": {
                "root_display": "{" + ", ".join(list(root)) + "}",
                "pattern_formula": f"Root({root[0] if len(root) > 0 else '?'}-{root[1] if len(root) > 1 else '?'}-{root[2] if len(root) > 2 else '?'})",
                "affix_formula": f"Prefix({'+'.join(prefixes) if prefixes else 'ø'}) + Stem + Suffix({'+'.join(suffixes) if suffixes else 'ø'})"
            }
        }
        return self._attach_classical_fields(result)
