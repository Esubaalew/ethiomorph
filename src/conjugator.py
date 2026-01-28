"""
EthioMorph Conjugator - Research-Grade Word Generator
=====================================================
Authentic Ge'ez verb morphology engine with proper suffix fusion and
dynamic vowel shifting based on Unicode ordering.

This module implements the core logic for generating conjugated Ge'ez verbs
across different classes (Type A, B, C, Quad, etc.) and tenses.

Key Features:
- Dynamic Vowel Shifting (Unicode Math)
- Suffix Fusion Rules (e.g., -u + 6th order -> 2nd order)
- Laryngeal/Guttural Adjustments
- Prefix Handling for Derived Stems

Esubalew Chekol
"""

import json
import os
from src.decomposer import (
    devowelize, get_char_order, get_char_by_order,
    get_consonant_skeleton, detect_verb_home
)

get_vowel_order = get_char_order

VOWEL_SUFFIX_MAP = {
    'ኡ': 2,
    'ኣ': 4,
    'ኢ': 3,
}

LARYNGEALS = set(['ሀ', 'ሐ', 'ኀ', 'አ', 'ዐ'])


class EthioMorphGenerator:
    """
    Research-grade Ge'ez verb conjugator.
    
    Generates words using mathematical vowel-order transformations
    with proper handling of suffix fusion rules and laryngeal adjustments.
    """
    
    def __init__(self):
        """Initialize the generator by loading templates and lexicon data."""
        self.templates = {}
        self.lexicon = {}
        self.lexicon_full = {}
        self._load_data()
    
    def _load_data(self):
        """Load templates, stems, and lexicon from the data directory."""
        try:
            base_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
            
            with open(os.path.join(base_dir, 'templates.json'), 'r', encoding='utf-8') as f:
                self.templates = json.load(f)
                
            with open(os.path.join(base_dir, 'stems.json'), 'r', encoding='utf-8') as f:
                self.stems_data = json.load(f).get('stems', {})
                
            with open(os.path.join(base_dir, 'lexicon.json'), 'r', encoding='utf-8') as f:
                lex_data = json.load(f)
                for entry in lex_data.get('roots', []):
                    self.lexicon[entry['root']] = entry.get('type', 'type_a')
                    self.lexicon_full[entry['root']] = entry
                    
        except FileNotFoundError:
            print("Warning: Data files (templates, stems, or lexicon) not found.")
    
    @staticmethod
    def change_order(char, target_order):
        """
        Shifts a Ge'ez character to a specific vowel order (1-7).
        
        Args:
            char: The base character.
            target_order: The target order (1-7) or "DROP".
            
        Returns:
            The modified character, or empty string if DROP.
        """
        if target_order == "DROP":
            return ""
        base = devowelize(char)
        return get_char_by_order(base, target_order)
    
    def _detect_weak_root(self, root_chars):
        """
        Detect if a root is a weak (hollow or weak initial) verb.
        
        Args:
            root_chars: List of root characters.
            
        Returns:
            Type information dict if weak, else None.
        """
        if len(root_chars) >= 2:
            c2 = root_chars[1]
            if c2 == 'ወ':
                return {"type": "hollow_w", "radical": "ወ", "description": "Middle-W hollow verb"}
            elif c2 == 'የ':
                return {"type": "hollow_y", "radical": "የ", "description": "Middle-Y hollow verb"}
        
        if len(root_chars) >= 1 and root_chars[0] == 'ወ':
            return {"type": "weak_initial", "radical": "ወ", "description": "Initial-W weak verb"}
        
        return None
    
    def _apply_fusion(self, final_base, final_target_order, suffix):
        """
        Apply Ge'ez suffix fusion rules.
        
        Fusion occurs when a vowel-starting suffix meets a 6th order final radical.
        
        Args:
            final_base: The base consonant of the final radical.
            final_target_order: The intended order of the final radical.
            suffix: The suffix being appended.
            
        Returns:
            Tuple of (final_char, remaining_suffix, is_fused).
        """
        if final_target_order != 6:
            final_char = self.change_order(final_base, final_target_order)
            return final_char, suffix, False

        if suffix in VOWEL_SUFFIX_MAP:
            fusion_order = VOWEL_SUFFIX_MAP[suffix]
            fused_char = self.change_order(final_base, fusion_order)
            return fused_char, "", True

        final_char = self.change_order(final_base, 6)
        return final_char, suffix, False
    
    def _apply_suffix_fusion(self, c3_base, c3_order, suffix):
        """Legacy wrapper for _apply_fusion targeting C3."""
        return self._apply_fusion(c3_base, c3_order, suffix)
    
    def _handle_prefixes(self, root):
        """
        Detect and strip known prefixes from the root for processing.
        
        Args:
            root: The input root string.
            
        Returns:
            Tuple of (clean_root, prefix_chars).
        """
        prefixes = ["አን", "አስተ", "ተ", "አ", "ነ"]
        prefixes.sort(key=len, reverse=True)
        
        for p in prefixes:
            if root.startswith(p) and len(root) > len(p):
                return root[len(p):], p
                
        return root, ""
    
    def _identify_stem(self, prefix, original_root):
        """
        Identify the verb stem (1-5) based on prefix pattern.
        
        Ge'ez has 5 main verb stems (አምዶች):
        - Stem I:   Basic (ቀዳማይ)           - No prefix
        - Stem II:  Passive (ተገብሮ)         - ተ- prefix  
        - Stem III: Causative (አሳሳቢ)       - አ- prefix
        - Stem IV:  Causative-Passive (አስተ) - አስተ- prefix
        - Stem V:   Reciprocal (ተሣሣቢ)      - ተ- with C1=4th order
        
        Args:
            prefix: The detected prefix string.
            original_root: The original root for pattern analysis.
            
        Returns:
            Dict with stem number, name, and template suffix.
        """
        # Check for reciprocal pattern (ተ- prefix + C1 with 4th order vowel)
        if prefix == "ተ":
       
            clean = original_root[len(prefix):]
            if clean and len(clean) >= 1:
                c1_order = get_vowel_order(clean[0])
                if c1_order == 4:
                    return {
                        "number": 5,
                        "name": "ተሣሣቢ (Reciprocal)",
                        "geez_name": "ተሣሣቢ ግንድ",
                        "english_name": "Reciprocal Stem",
                        "template_suffix": "reciprocal",
                        "description": "Mutual/reciprocal action"
                    }
            # Default: passive
            return {
                "number": 2,
                "name": "ተገብሮ (Passive)",
                "geez_name": "ተገብሮ ግንድ",
                "english_name": "Passive/Reflexive Stem",
                "template_suffix": "passive",
                "description": "Passive or reflexive action"
            }
        
        if prefix == "አስተ":
            return {
                "number": 4,
                "name": "አስተሳሳቢ (Causative-Passive)",
                "geez_name": "አስተሳሳቢ ግንድ",
                "english_name": "Causative-Passive Stem",
                "template_suffix": "aste",
                "description": "Causative-passive or intensive action"
            }
        
        if prefix == "አ":
            return {
                "number": 3,
                "name": "አሳሳቢ (Causative)",
                "geez_name": "አሳሳቢ ግንድ",
                "english_name": "Causative Stem",
                "template_suffix": "causative",
                "description": "Causing someone to perform action"
            }
        
    
        return {
            "number": 1,
            "name": "ቀዳማይ (Basic)",
            "geez_name": "ቀዳማይ ግንድ",
            "english_name": "Basic Stem",
            "template_suffix": "",
            "description": "Basic active voice"
        }

    def _apply_laryngeal_rules(self, char, order, position, tense, verb_type, features=None):
        """
        Apply Ge'ez laryngeal (guttural) rules affecting vowel orders.
        
        Laryngeal consonants (ሀ, ሐ, ኀ, አ, ዐ) cause vowel shifts in certain contexts:
        - Jussive: Shift to 4th order (ራብዕ) when laryngeal is present
        - Imperfective: May drop certain radicals
        
        Args:
            char: The character being processed.
            order: The target order.
            position: Radical position (C1, C2, etc.).
            tense: Grammatical tense.
            verb_type: Verb classification.
            features: Dict of verb features (has_laryngeal, is_hollow, etc.).
            
        Returns:
            The adjusted order or "DROP".
        """
        base = devowelize(char)
        features = features or {}
        
        
        if verb_type == "type_d" and tense == "imperfective" and position == "C2":
            return "DROP"
        
        
        if features.get('has_laryngeal'):
            laryngeal_positions = features.get('laryngeal_positions', [])
            
           
            if tense == "jussive" and base in LARYNGEALS:
                return 4 
            
          
            if tense == "imperfective" and position == "C2" and f"C2={base}" in str(laryngeal_positions):
              
                return 4
             
        return order

    def generate_word(self, root, tense, subject_key, verb_type=None, verb_home=None):
        """
        Generate a conjugated Ge'ez word with full derivation metadata.
        
        Uses algorithmic verb home detection to apply feature-specific rules
        (laryngeal vowel shifts, hollow verb handling) during conjugation.
        
        Args:
            root: The root (3 or 4 letters).
            tense: 'perfective', 'imperfective', 'jussive', 'imperative'.
            subject_key: '3sm', '1p', '2sf', etc.
            verb_type: The verb class. If None, uses verb_home detection.
            verb_home: Pre-computed verb home dict (optional).
            
        Returns:
            Dict with word and complete derivation metadata.
        """
        clean_root, root_prefix = self._handle_prefixes(root)
        root_chars = [devowelize(c) for c in root]
        
        if not verb_home:
            skeleton = get_consonant_skeleton(root)
            verb_home = detect_verb_home(skeleton, root)
        
        features = verb_home.get('features', {})
        
        if not verb_type:
            verb_type = self.lexicon.get(root) or verb_home.get('type') or "type_a"
        
        is_derived_stem_template = any(
            suffix in verb_type for suffix in ["_passive", "_causative", "_aste", "_reciprocal"]
        )
        
        prefix_adjustment = ""
        if root_prefix:
            clean_root_chars = [devowelize(c) for c in clean_root]
            root_chars = clean_root_chars
            if not is_derived_stem_template:
                prefix_adjustment = root_prefix
        
        if len(root_chars) < 3:
             return {"error": f"Root must be at least 3 letters (Got '{root}')"}
        
        type_data = self.templates.get(verb_type)
        if not type_data:
            return {"error": f"Unknown verb type '{verb_type}'"}

        tense_data = type_data.get(tense)
        if not tense_data or tense == "_meta":
            return {"error": f"Unknown tense '{tense}' for type '{verb_type}'"}
        
        subjects = tense_data.get("subjects", {})
        subject_data = subjects.get(subject_key)
        if not subject_data:
            return {"error": f"Unknown subject '{subject_key}' for tense '{tense}'"}
        
        template_name = tense_data.get("template_name", tense)
        geez_name = tense_data.get("geez_name", "")
        cv_template = tense_data.get("cv_template", "")
        gemination = tense_data.get("gemination", None)
        
        subject_prefix = subject_data.get("prefix", "")
        suffix = subject_data.get("suffix", "")
        vowel_map = subject_data.get("vowel_map", {})
        morphological_rule = subject_data.get("morphological_rule", "")
        subject_label = subject_data.get("label", {})
        
        weak_info = self._detect_weak_root(root_chars) if len(root_chars) == 3 else None
        
        result_chars = []
        vowel_shifts = []
        fusion_info = None
        
        final_prefix = subject_prefix
        
        if prefix_adjustment:
            if prefix_adjustment == "አን":
                if subject_prefix == "ይ": final_prefix = "ያን"
                elif subject_prefix == "ት": final_prefix = "ታን"
                elif subject_prefix == "እ": final_prefix = "አን"
                elif subject_prefix == "ን": final_prefix = "ናን"
                else: final_prefix = subject_prefix + prefix_adjustment
                
                if tense == "perfective":
                    final_prefix = prefix_adjustment
                    
            elif prefix_adjustment == "አስተ":
                if subject_prefix == "ይ": final_prefix = "ያስተ"
                elif subject_prefix == "ት": final_prefix = "ታስተ"
                elif subject_prefix == "እ": final_prefix = "አስተ"
                elif subject_prefix == "ን": final_prefix = "ናስተ"
                else: final_prefix = subject_prefix + prefix_adjustment
                
                if tense == "perfective":
                    final_prefix = prefix_adjustment
            
            # Causative "አ" prefix: ይ→ያ, ት→ታ, እ→አ, ን→ና
            elif prefix_adjustment == "አ":
                if subject_prefix == "ይ": final_prefix = "ያ"
                elif subject_prefix == "ት": final_prefix = "ታ"
                elif subject_prefix == "እ": final_prefix = "አ"
                elif subject_prefix == "ን": final_prefix = "ና"
                else: final_prefix = subject_prefix + prefix_adjustment
                
                if tense == "perfective":
                    final_prefix = prefix_adjustment

            else:
                final_prefix = subject_prefix + prefix_adjustment

        if final_prefix:
            result_chars.append(final_prefix)
        
        radicals = ["C1", "C2", "C3"]
        if len(root_chars) >= 4:
            radicals.append("C4")
            
        last_radical_key = radicals[-1]

        if weak_info and weak_info["type"] in ("hollow_w", "hollow_y") and tense == "perfective" and len(root_chars) == 3:
            weak_rules = self.templates.get("weak_root_rules", {}).get(weak_info["type"], {})
            transform = weak_rules.get("perfective_transform", {})
            
            c1_order = transform.get("C1", vowel_map.get("C1", 1))
            c3_order = transform.get("C3", vowel_map.get("C3", 1))
            
            c1_out = self.change_order(root_chars[0], c1_order)
            result_chars.append(c1_out)
            vowel_shifts.append({
                "consonant": "C1",
                "base": root_chars[0],
                "order": c1_order,
                "result": c1_out,
                "note": f"hollow verb: takes order {c1_order}"
            })
            
            vowel_shifts.append({
                "consonant": "C2",
                "base": root_chars[1],
                "order": "DROP",
                "result": "",
                "note": "hollow verb: middle radical dropped"
            })
            
            c3_out, suffix_out, fused = self._apply_suffix_fusion(root_chars[2], c3_order, suffix)
            result_chars.append(c3_out)
            vowel_shifts.append({
                "consonant": "C3",
                "base": root_chars[2],
                "order": c3_order if not fused else f"{c3_order}→{VOWEL_SUFFIX_MAP.get(suffix, '?')}",
                "result": c3_out,
                "note": "suffix fusion applied" if fused else ""
            })
            
            if fused:
                fusion_info = {"original_suffix": suffix, "fused_with": "C3", "result": c3_out}
            suffix = suffix_out
            
        else:
            for i, key in enumerate(radicals):
                if i < len(root_chars):
                    base = root_chars[i]
                    order = vowel_map.get(key, 1)
                    
                    # Weak Initial C1-Drop Rule: ወለደ → ይልድ (C1 drops in Jussive/Imperative)
                    # When verb is weak_initial (C1=ወ), drop C1 in jussive and imperative
                    if key == "C1" and weak_info and weak_info.get("type") == "weak_initial":
                        if tense in ["jussive", "imperative"]:
                            vowel_shifts.append({
                                "consonant": key,
                                "base": base,
                                "order": "DROP",
                                "result": "",
                                "note": "Weak Initial: C1 (ወ) drops in Jussive/Imperative"
                            })
                            continue
                    
                    order = self._apply_laryngeal_rules(base, order, key, tense, verb_type, features)
                    
                    if order == "DROP":
                        vowel_shifts.append({
                            "consonant": key,
                            "base": base,
                            "order": "DROP",
                            "result": "",
                            "note": "Laryngeal/Type Rule Dropped"
                        })
                        continue

                    if key == last_radical_key and suffix:
                        final_out, suffix_out, fused = self._apply_fusion(base, order, suffix)
                        result_chars.append(final_out)
                        
                        if fused:
                            fusion_info = {"original_suffix": suffix, "fused_with": key, "result": final_out}
                            suffix = suffix_out
                        
                        vowel_shifts.append({
                            "consonant": key,
                            "base": base,
                            "order": order if not fused else f"{order}→{VOWEL_SUFFIX_MAP.get(subject_data.get('suffix', ''), '?')}",
                            "result": final_out,
                            "note": "suffix fusion applied" if fused else ""
                        })
                    else:
                        shifted = self.change_order(base, order)
                        result_chars.append(shifted)
                        
                        vowel_shifts.append({
                            "consonant": key,
                            "base": base,
                            "order": order,
                            "result": shifted,
                            "note": ""
                        })
        
        if suffix:
            result_chars.append(suffix)
        
        word = "".join(result_chars)
        
        derivation = {
            "root": root_chars,
            "root_display": "{" + ", ".join(root_chars) + "}",
            "root_type": weak_info["type"] if weak_info else "strong",
            "verb_type": verb_type,
            "verb_home": verb_home,
            "tense": {
                "name": tense,
                "template_name": template_name,
                "geez_name": geez_name,
                "cv_template": cv_template,
                "gemination": gemination
            },
            "subject": {
                "key": subject_key,
                "geez": subject_label.get("geez", ""),
                "english": subject_label.get("english", "")
            },
            "vowel_shifts": vowel_shifts,
            "morphological_rule": morphological_rule,
            "applied_pattern": ", ".join([str(vowel_map.get(k, '-')) for k in radicals]),
            "prefix": final_prefix,
            "suffix": subject_data.get("suffix", ""),
            "fusion": fusion_info,
            "features_applied": {
                "laryngeal_shift": features.get('has_laryngeal', False),
                "hollow_handling": features.get('is_hollow', False),
                "weak_initial_drop": weak_info.get("type") == "weak_initial" if weak_info else False,
                "causative_prefix": prefix_adjustment == "አ"
            }
        }
        
        return {
            "word": word,
            "derivation": derivation
        }
    
    def generate_derived(self, root, derived_class, verb_type=None):
        """
        Generates derived nominals (Participles, Infinitives, etc.) based on verb type.
        
        Args:
            root: The verb root.
            derived_class: 'infinitive', 'active_participle', 'passive_participle', 
                          'instrumental', 'verbal_noun', 'abstract_noun'.
            verb_type: The verb class (optional).
            
        Returns:
            Dict with generated word and metadata.
        """
        if not verb_type:
            verb_type = self.lexicon.get(root, "type_a")
            
        type_data = self.templates.get(verb_type)
        if not type_data:
            return {"error": f"Unknown verb type '{verb_type}'"}
            
        derived_templates = type_data.get('derived', {})
        template = derived_templates.get(derived_class)
        
        if not template:
            return {"error": f"Derived form '{derived_class}' not defined for '{verb_type}'"}
            
        root_chars = [devowelize(c) for c in root]
        
        clean_root, root_prefix = self._handle_prefixes(root)
        if len(root_chars) > 4:
            root_chars = [devowelize(c) for c in clean_root]

        vowel_map = template.get("pattern", {})
        prefix = template.get("prefix", "")
        suffix = template.get("suffix", "")
        
        result_chars = []
        if prefix:
            result_chars.append(prefix)
            
        radicals = ["C1", "C2", "C3"]
        if len(root_chars) >= 4:
            radicals.append("C4")
            
        for i, key in enumerate(radicals):
            if i < len(root_chars):
            
                if key not in vowel_map:
                    continue
                base = root_chars[i]
                order = vowel_map.get(key, 1)
                result_chars.append(self.change_order(base, order))
                
        if suffix:
            result_chars.append(suffix)
            
        return {
            "word": "".join(result_chars),
            "template": template.get("template"),
            "type": verb_type,
            "class": derived_class
        }

    def expand_root(self, root, verb_type=None):
        """
        Generate the full conjugation matrix including derived forms.
        
        Uses algorithmic verb home detection to determine verb class and features,
        then applies appropriate conjugation rules for each tense/subject.
        
        Handles derived stems:
        - ተ- prefix → Passive/Reflexive stem (ተገብሮ)
        - አ- prefix → Causative stem (አሳሳቢ)
        - አስተ- prefix → Causative-Passive stem
        
        Args:
            root: The verb root.
            verb_type: The verb class (optional, overrides detection).
            
        Returns:
            Dict with complete matrix of conjugations and derived forms.
        """
        clean_root, stem_prefix = self._handle_prefixes(root)
        
        stem_info = self._identify_stem(stem_prefix, root)
        stem_number = stem_info['number']
        stem_suffix = stem_info['template_suffix']
        
        analysis_root = clean_root if stem_prefix else root
        root_chars = [devowelize(c) for c in analysis_root]
        
        if len(root_chars) < 3:
             return {"error": f"Root must be at least 3 letters (Got '{root}')"}

        skeleton = get_consonant_skeleton(analysis_root)
        verb_home = detect_verb_home(skeleton, analysis_root)
        features = verb_home.get('features', {})
        
        features['stem_number'] = stem_number
        features['stem_prefix'] = stem_prefix or None
        features['stem_type'] = stem_info['name']
        
       
        base_type = self.lexicon.get(analysis_root) or verb_home.get('type') or "type_a"
        
       
        if stem_suffix and f"{base_type}_{stem_suffix}" in self.templates:
            verb_type = f"{base_type}_{stem_suffix}"
        elif not verb_type:
            verb_type = base_type

        weak_info = self._detect_weak_root(root_chars) if len(root_chars) == 3 else None
        
        result = {
            "_meta": {
                "root": root,
                "base_root": analysis_root,
                "root_consonants": root_chars,
                "root_type": weak_info["type"] if weak_info else "strong",
                "verb_type": verb_type,
                "stem": {
                    "number": stem_info['number'],
                    "name": stem_info['name'],
                    "geez_name": stem_info['geez_name'],
                    "prefix": stem_prefix or None,
                    "description": stem_info['description']
                },
                "verb_home": verb_home,
                "meaning": self.lexicon_full.get(analysis_root, {}).get('meaning'),
                "framework_version": "2.4",
                "note": "Authentic Ge'ez morphology with 5-stem system support"
            }
        }
        
        type_data = self.templates.get(verb_type)
        if not type_data:
            return {"error": f"Unknown verb type '{verb_type}'"}

        for tense in ["perfective", "imperfective", "jussive", "imperative"]:
            tense_data = type_data.get(tense)
            if not tense_data:
                continue
            
            subjects = tense_data.get("subjects", {})
            
            result[tense] = {
                "_template": {
                    "name": tense_data.get("template_name", ""),
                    "geez_name": tense_data.get("geez_name", ""),
                    "semantic": tense_data.get("semantic", ""),
                    "cv_template": tense_data.get("cv_template", "")
                },
                "conjugations": {}
            }
            
            for subject_key in subjects:
                gen_root = analysis_root if stem_suffix else root
                gen_result = self.generate_word(gen_root, tense, subject_key, verb_type, verb_home)
                if "error" not in gen_result:
                    result[tense]["conjugations"][subject_key] = gen_result
        
        result["derived"] = {}
        derived_keys = [
            "infinitive", "active_participle", "passive_participle", 
            "instrumental", "verbal_noun", "abstract_noun",
            "verbal_noun_alt", "causative_agent", "passive_adj", "place_noun"
        ]
        
        for key in derived_keys:
            gen_result = self.generate_derived(root, key, verb_type)
            if "error" not in gen_result:
                result["derived"][key] = gen_result

        return result
    
    def generate_stem(self, root, stem_code):
        """
        Generate a specific derived stem (e.g., Causative).
        
        Args:
            root: The verb root.
            stem_code: The stem identifier.
            
        Returns:
            Dict with generated stem word and metadata.
        """
        if len(root) < 3:
            return {"error": "Root too short"}
        
        stem_def = self.stems_data.get(stem_code)
        if not stem_def:
            return {"error": f"Unknown stem code {stem_code}"}
        
        root_chars = [devowelize(c) for c in root]
        prefix = stem_def.get("prefix", "")
        vowel_map = stem_def.get("vowel_map", {})
        
        result_chars = [prefix]
        radicals = ["C1", "C2", "C3"]
        if len(root_chars) >= 4:
            radicals.append("C4")

        for i, key in enumerate(radicals):
             if i < len(root_chars):
                order = vowel_map.get(key, 1)
                char = self.change_order(root_chars[i], order)
                result_chars.append(char)
            
        word = "".join(result_chars)
        return {
            "root": root,
            "stem_code": stem_code,
            "stem_name": stem_def["name"],
            "geez_name": stem_def["geez_name"],
            "meaning": stem_def["meaning"],
            "word": word
        }

    def expand_stems(self, root):
        """Generate all derived stems for a root."""
        results = {}
        for code in self.stems_data:
            results[code] = self.generate_stem(root, code)
        return results

    def expand_root_simple(self, root, verb_type=None):
        """
        Generate a simple conjugation matrix (backwards compatible).
        
        Uses algorithmic verb home detection for feature-based conjugation.
        
        Args:
            root: The verb root.
            verb_type: The verb class (optional).
        
        Returns:
            Flat dict of tense -> subject -> word.
        """
        root_chars = [devowelize(c) for c in root]
        if len(root_chars) < 3:
             return {"error": f"Root must be at least 3 letters (Got '{root}')"}
        
    
        skeleton = get_consonant_skeleton(root)
        verb_home = detect_verb_home(skeleton, root)
        
        if not verb_type:
            verb_type = self.lexicon.get(root) or verb_home.get('type') or "type_a"
        
        result = {}
        key_map = {
            "3sm": "he", "3sf": "she",
            "2sm": "you_m", "2sf": "you_f",
            "1s": "I", "1p": "we",
            "3pm": "they_m", "3pf": "they_f",
            "2pm": "you_pl_m", "2pf": "you_pl_f"
        }
        
        type_data = self.templates.get(verb_type)
        if not type_data:
             return {"error": f"Unknown verb type '{verb_type}'"}

        for tense in ["perfective", "imperfective", "jussive", "imperative"]:
            tense_data = type_data.get(tense)
            if not tense_data:
                continue
            
            subjects = tense_data.get("subjects", {})
            result[tense] = {}
            
            for subject_key in subjects:
                gen_result = self.generate_word(root, tense, subject_key, verb_type, verb_home)
                if "error" not in gen_result:
                    old_key = key_map.get(subject_key, subject_key)
                    result[tense][old_key] = gen_result["word"]
        
        result['derived'] = {}
        derived_keys = [
            "infinitive", "active_participle", "passive_participle", 
            "instrumental", "verbal_noun", "abstract_noun",
            "verbal_noun_alt", "causative_agent", "passive_adj", "place_noun"
        ]
        for key in derived_keys:
            gen_result = self.generate_derived(root, key, verb_type)
            if "error" not in gen_result:
                result['derived'][key] = gen_result['word']

        return result


GeezConjugator = EthioMorphGenerator
