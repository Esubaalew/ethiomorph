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
from src.grammar_loader import GrammarIndex


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
        self.laryngeals = {'ሀ', 'ሐ', 'ኀ', 'አ', 'ዐ', 'ህ', 'ሕ', 'ኅ', 'ዕ'}
        
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
            'ክ', 'ን', 'ት', 'ም', 'አት', 'ተ', 'ዩ',
        ]

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

        return {
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
    
    def _reconstruct_laryngeal_middle(self, skeleton):
        """
        Reconstruct a laryngeal middle root from a 2-consonant skeleton.
        
        When C2 is a laryngeal (ሀ, ሐ, ኀ, etc.), it often disappears in certain
        conjugations (Jussive, Imperative). This method attempts to find the
        full root by checking against known laryngeal-middle roots.
        
        Example: ብለ → ብህለ (ብ + ህ + ለ)
        
        Args:
            skeleton: 2-consonant skeleton (e.g., "ብለ")
            
        Returns:
            Tuple of (reconstructed_root, laryngeal_char) or (None, None)
        """
        if len(skeleton) != 2:
            return None, None
        
        c1 = devowelize(skeleton[0])
        c3 = devowelize(skeleton[1]) if len(skeleton) > 1 else ''
        
        # Try each laryngeal as potential C2
        laryngeal_bases = ['ሀ', 'ሐ', 'ኀ', 'አ', 'ዐ']
        
        for laryngeal in laryngeal_bases:
            candidate = c1 + laryngeal + c3
            if candidate in self.laryngeal_middle_roots:
                return candidate, laryngeal
            # Also check lexicon
            if candidate in self.lexicon_roots:
                root_info = self.lexicon_roots[candidate]
                if root_info.get('type') in ['laryngeal_middle', 'laryngeal']:
                    return candidate, laryngeal
        
        # Heuristic: if no match found but pattern suggests laryngeal
        # Common laryngeal-middle pattern: ብለ → ብህለ
        if c1 == 'ብ' and c3 == 'ለ':
            return 'ብህለ', 'ህ'
        
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
            return candidates[0]

        if pattern_name in {"imperfective", "jussive"} and stem and get_char_order(stem[0]) == 6:
            for candidate in candidates:
                if self.lexicon_roots[candidate].get("type") == "type_a":
                    return candidate

        order_surface = source or stem
        if order_surface:
            c1_order = get_char_order(order_surface[0])
            if c1_order:
                order_matches = [
                    candidate for candidate in candidates
                    if get_char_order(candidate[0]) == c1_order
                ]
                if len(order_matches) == 1:
                    return order_matches[0]

        for candidate in candidates:
            if candidate in self.hollow_w_roots or candidate in self.hollow_y_roots:
                return candidate

        for candidate in candidates:
            root_type = self.lexicon_roots[candidate].get("type", "")
            if root_type and root_type not in ("type_a", "strong", "unknown"):
                return candidate

        grammar_pick = self.grammar.resolve_skeleton(
            skeleton, source=source, pattern_name=pattern_name
        )
        if grammar_pick and grammar_pick in candidates:
            return grammar_pick

        return candidates[0]

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
            
            for prefix in self.prefixes:
                if current_word.startswith(prefix):
                    remaining = current_word[len(prefix):]
                    remaining_skeleton = get_consonant_skeleton(remaining)
                    
                    if prefix == 'መ':
                        if current_word in self.nouns:
                            continue
                            
                        if len(remaining) > 0:
                            last_char = remaining[-1]
                            if get_char_order(last_char) == 1 and len(remaining_skeleton) >= 3:
                                skeleton_full = get_consonant_skeleton(current_word)
                                if skeleton_full in self.quadriliterals:
                                    continue

                    if len(remaining_skeleton) >= 3:
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
                    elif len(remaining_skeleton) == 2 and self._is_weak_root_candidate(remaining):
                        derivation_steps.append({
                            "action": "strip_prefix",
                            "affix": prefix,
                            "before": current_word,
                            "after": remaining,
                            "rule": f"Prefix '{prefix}' stripped (weak root candidate)"
                        })
                        found_prefixes.append(prefix)
                        current_word = remaining
                        changed = True
                        break
            
            if changed:
                continue

            for suffix in self.suffixes:
                if current_word.endswith(suffix):
                    remaining = current_word[:-len(suffix)]
                    remaining_skeleton = get_consonant_skeleton(remaining)
                    
                    if len(remaining_skeleton) >= 3:
                        derivation_steps.append({
                            "action": "strip_suffix",
                            "affix": suffix,
                            "before": current_word,
                            "after": remaining,
                            "rule": f"Suffix '{suffix}' stripped (skeleton >= 3)"
                        })
                        found_suffixes.append(suffix)
                        current_word = remaining
                        changed = True
                        break
                    elif len(remaining_skeleton) == 2:
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

    def identify_verb_pattern(self, stem, prefixes):
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
                "geez_name": "ካልኣይ አንቀጽ",
                "english_name": "Imperfective",
                "stem_number": 1,
                "description": "Stem I: Basic ongoing/habitual action"
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
        
        # Perfective: default citation form
        if len(skeleton) >= 3 and len(stem) > 0 and get_char_order(stem[-1]) == 1:
            return {
                "name": "perfective",
                "geez_name": "ቀዳማይ አንቀጽ",
                "english_name": "Perfective",
                "stem_number": 1,
                "description": "Stem I: Basic completed action"
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

        canonical_initial = self._resolve_skeleton_citation(
            skeleton_initial, source=normalized, stem=normalized
        ) or self._canonicalize_root(skeleton_initial, source=normalized, stem=normalized)
        if canonical_initial in self.lexicon_roots and not (len(skeleton_initial) == 2 and has_order_signal):
            derivation_steps.append({
                "step": 2,
                "action": "lexicon_match",
                "description": "Direct lexicon lookup",
                "before": normalized,
                "after": canonical_initial,
                "rule": f"Found in lexicon: {self.lexicon_roots[canonical_initial].get('meaning', 'N/A')}"
            })
            return self._build_result(word, canonical_initial, normalized, [], [], derivation_steps, "lexicon")

        if normalized in self.nouns:
            noun_entry = self.nouns[normalized]
            root = noun_entry.get('root', normalized)
            root_type = "derived_noun" if 'root' in noun_entry else "noun"
            skeleton = get_consonant_skeleton(root)
            verb_home = detect_verb_home(skeleton, root)
            
            return {
                "input": word,
                "root": root,
                "root_consonants": list(skeleton),
                "root_type": root_type,
                "verb_home": verb_home,
                "meaning": noun_entry.get('meaning', "Noun"),
                "confidence": 1.0,
                "analysis": {
                    "stem": normalized,
                    "pattern": {"name": "noun", "geez_name": "ስም", "english_name": "Noun", "description": "Protected Noun"},
                    "prefixes": [],
                    "suffixes": [],
                    "method": "lexicon_noun"
                },
                "derivation_path": [{
                    "step": 1,
                    "action": "noun_match",
                    "description": "Protected Noun Lookup",
                    "before": normalized,
                    "after": root,
                    "rule": f"Derived from root '{root}' (Lexicon)"
                }],
                "research_notation": {
                    "root_display": "{" + ", ".join(list(skeleton)) + "}",
                    "pattern_formula": "Noun",
                    "affix_formula": "Stem"
                }
            }

        stem, prefixes, suffixes, affix_steps = self.strip_affixes(normalized)
        for i, step in enumerate(affix_steps):
            step["step"] = len(derivation_steps) + 1 + i
            derivation_steps.append(step)
        
        skeleton = get_consonant_skeleton(stem)
        derivation_steps.append({
            "step": len(derivation_steps) + 1,
            "action": "devowelize",
            "description": "Extract consonant skeleton",
            "before": stem,
            "after": skeleton,
            "rule": "Remove vowel orders to get base consonants"
        })
        
        root = skeleton
        
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

        return self._build_result(word, root, stem, prefixes, suffixes, derivation_steps, "derived")

    def _build_result(self, word, root, stem, prefixes, suffixes, derivation_steps, method):
        """
        Build the standardized result dictionary with algorithmic verb type detection.
        
        Includes the 'verb_home' field which algorithmically detects the verb class
        based on radical count and vowel quality (C1 order), without requiring 
        lexicon lookup. Also detects causative prefixes.
        """
        pattern = self.identify_verb_pattern(stem, prefixes)
        canonical_root = self._canonicalize_root(
            root,
            source=word,
            stem=stem,
            pattern_name=pattern.get("name"),
        )
        if canonical_root != root:
            citation_via = (
                "skeleton citation lookup"
                if normalize_geez(get_consonant_skeleton(root)) in self.skeleton_lookup
                else "homophone-normalized root mapped to lexicon citation form"
            )
            derivation_steps.append({
                "step": len(derivation_steps) + 1,
                "action": "canonicalize_root",
                "description": "Resolve to lexicon canonical orthography",
                "before": root,
                "after": canonical_root,
                "rule": citation_via
            })
            root = canonical_root

        root_type = self._get_root_type(root)
        
        lexicon_entry = self.lexicon_roots.get(root, {})
        meaning = lexicon_entry.get('meaning', None)
        if not meaning:
            meaning = self.grammar.primary_gloss(root)

        grammar_ref = self.grammar.reference(root)
        grammar_patterns = self.grammar.grammar_patterns(root)
        
        verb_home = detect_verb_home(root, stem)
        
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
        
        return {
            "input": word,
            "root": root,
            "root_consonants": list(get_consonant_skeleton(root)),
            "root_type": root_type,
            "verb_home": verb_home,
            "meaning": meaning,
            "confidence": 0.95 if method == "lexicon" else 0.85 if method == "derived" else 0.70,
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
