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


class GeezStemmer:
    """
    Ge'ez morphological analyzer.
    
    Provides complete derivation paths showing how roots are extracted through 
    normalization, affix stripping, and weak root reconstruction.
    """
    
    def __init__(self):
        """Initialize the stemmer by loading the lexicon."""
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
                        
        except FileNotFoundError:
            print("Warning: lexicon.json not found. Using empty lexicon.")

        self.nouns = {}
        try:
            lexicon_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'lexicon.json')
            with open(lexicon_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for entry in data.get('nouns', []):
                    self.nouns[entry['word']] = entry
        except Exception:
            pass

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
            'ይ', 'ት', 'እ', 'ን', 'ል',
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
        
        if len(normalized) == 1:
            one_char_map = {
                'ፃ': ('ወጸአ', "Imperative of ወጸአ 'to go out'"),
                'ጻ': ('ወጸአ', "Imperative of ወጸአ 'to go out'"),
                'ሖ': ('ሀወረ', "Imperative of ሀወረ 'to go'"),
                'ሆ': ('ሀወረ', "Imperative of ሀወረ 'to go'")
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
        if skeleton_initial in self.lexicon_roots:
            derivation_steps.append({
                "step": 2,
                "action": "lexicon_match",
                "description": "Direct lexicon lookup",
                "before": normalized,
                "after": skeleton_initial,
                "rule": f"Found in lexicon: {self.lexicon_roots[skeleton_initial].get('meaning', 'N/A')}"
            })
            return self._build_result(word, skeleton_initial, normalized, [], [], derivation_steps, "lexicon")

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
            # Try laryngeal middle reconstruction if still 2 letters
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
                # Try weak initial reconstruction
                candidate = 'ወ' + root
                if candidate in self.weak_initial_roots:
                    derivation_steps.append({
                        "step": len(derivation_steps) + 1,
                        "action": "reconstruct_weak_initial",
                        "description": "Reconstruct assimilated initial ወ",
                        "before": root,
                        "after": candidate,
                        "rule": f"2-letter stem matches weak-initial pattern. Restored ወ prefix."
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
        root_type = self._get_root_type(root)
        
        lexicon_entry = self.lexicon_roots.get(root, {})
        meaning = lexicon_entry.get('meaning', None)
        
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
            "root_consonants": list(root),
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
                "is_causative": is_causative
            },
            "derivation_path": derivation_steps,
            "research_notation": {
                "root_display": "{" + ", ".join(list(root)) + "}",
                "pattern_formula": f"Root({root[0] if len(root) > 0 else '?'}-{root[1] if len(root) > 1 else '?'}-{root[2] if len(root) > 2 else '?'})",
                "affix_formula": f"Prefix({'+'.join(prefixes) if prefixes else 'ø'}) + Stem + Suffix({'+'.join(suffixes) if suffixes else 'ø'})"
            }
        }
