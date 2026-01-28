"""
EthioMorph Decomposer - Unicode Character Utilities
===================================================
Provides low-level utilities for decomposing Ge'ez characters into their
base consonant and vowel order.

Esubalew Chekol
"""

DEVOWELIZATION_MAP = {}
ORDER_MAP = {}
REVOWELIZATION_MAP = {}


def _add_row(base, chars):
    """Populate character maps for a standard 7-order row."""
    for i, char in enumerate(chars):
        DEVOWELIZATION_MAP[char] = base
        ORDER_MAP[char] = i + 1
        REVOWELIZATION_MAP[(base, i + 1)] = char


_add_row('ሀ', ['ሀ', 'ሁ', 'ሂ', 'ሃ', 'ሄ', 'ህ', 'ሆ'])
_add_row('ለ', ['ለ', 'ሉ', 'ሊ', 'ላ', 'ሌ', 'ል', 'ሎ'])
_add_row('ሐ', ['ሐ', 'ሑ', 'ሒ', 'ሓ', 'ሔ', 'ሕ', 'ሖ'])
_add_row('መ', ['መ', 'ሙ', 'ሚ', 'ማ', 'ሜ', 'ም', 'ሞ'])
_add_row('ሠ', ['ሠ', 'ሡ', 'ሢ', 'ሣ', 'ሤ', 'ሥ', 'ሦ'])
_add_row('ረ', ['ረ', 'ሩ', 'ሪ', 'ራ', 'ሬ', 'ር', 'ሮ'])
_add_row('ሰ', ['ሰ', 'ሱ', 'ሲ', 'ሳ', 'ሴ', 'ስ', 'ሶ'])
_add_row('ሸ', ['ሸ', 'ሹ', 'ሺ', 'ሻ', 'ሼ', 'ሽ', 'ሾ'])
_add_row('ቀ', ['ቀ', 'ቁ', 'ቂ', 'ቃ', 'ቄ', 'ቅ', 'ቆ'])
_add_row('በ', ['በ', 'ቡ', 'ቢ', 'ባ', 'ቤ', 'ብ', 'ቦ'])
_add_row('ቨ', ['ቨ', 'ቩ', 'ቪ', 'ቫ', 'ቬ', 'ቭ', 'ቮ'])
_add_row('ተ', ['ተ', 'ቱ', 'ቲ', 'ታ', 'ቴ', 'ት', 'ቶ'])
_add_row('ቸ', ['ቸ', 'ቹ', 'ቺ', 'ቻ', 'ቼ', 'ች', 'ቾ'])
_add_row('ኀ', ['ኀ', 'ኁ', 'ኂ', 'ኃ', 'ኄ', 'ኅ', 'ኆ'])
_add_row('ነ', ['ነ', 'ኑ', 'ኒ', 'ና', 'ኔ', 'ን', 'ኖ'])
_add_row('ኘ', ['ኘ', 'ኙ', 'ኚ', 'ኛ', 'ኜ', 'ኝ', 'ኞ'])
_add_row('አ', ['አ', 'ኡ', 'ኢ', 'ኣ', 'ኤ', 'እ', 'ኦ'])
_add_row('ከ', ['ከ', 'ኩ', 'ኪ', 'ካ', 'ኬ', 'ክ', 'ኮ'])
_add_row('ኸ', ['ኸ', 'ኹ', 'ኺ', 'ኻ', 'ኼ', 'ኽ', 'ኾ'])
_add_row('ወ', ['ወ', 'ዉ', 'ዊ', 'ዋ', 'ዌ', 'ው', 'ዎ'])
_add_row('ዓ', ['ዓ', 'ዑ', 'ዒ', 'ዓ', 'ዔ', 'ዕ', 'ዖ'])
_add_row('ዘ', ['ዘ', 'ዙ', 'ዚ', 'ዛ', 'ዜ', 'ዝ', 'ዞ'])
_add_row('ዠ', ['ዠ', 'ዡ', 'ዢ', 'ዣ', 'ዤ', 'ዥ', 'ዦ'])
_add_row('የ', ['የ', 'ዩ', 'ዪ', 'ያ', 'ዬ', 'ይ', 'ዮ'])
_add_row('ደ', ['ደ', 'ዱ', 'ዲ', 'ዳ', 'ዴ', 'ድ', 'ዶ'])
_add_row('ጀ', ['ጀ', 'ጁ', 'ጂ', 'ጃ', 'ጄ', 'ጅ', 'ጆ'])
_add_row('ገ', ['ገ', 'ጉ', 'ጊ', 'ጋ', 'ጌ', 'ግ', 'ጎ'])
_add_row('ጠ', ['ጠ', 'ጡ', 'ጢ', 'ጣ', 'ጤ', 'ጥ', 'ጦ'])
_add_row('ጨ', ['ጨ', 'ጩ', 'ጪ', 'ጫ', 'ጬ', 'ጭ', 'ጮ'])
_add_row('ጰ', ['ጰ', 'ጱ', 'ጲ', 'ጳ', 'ጴ', 'ጵ', 'ጶ'])
_add_row('ጸ', ['ጸ', 'ጹ', 'ጺ', 'ጻ', 'ጼ', 'ጽ', 'ጾ'])
_add_row('ፀ', ['ፀ', 'ፁ', 'ጺ', 'ፃ', 'ፄ', 'ፅ', 'ፆ'])
_add_row('ፈ', ['ፈ', 'ፉ', 'ፊ', 'ፋ', 'ፌ', 'ፍ', 'ፎ'])
_add_row('ፐ', ['ፐ', 'ፑ', 'ፒ', 'ፓ', 'ፔ', 'ፕ', 'ፖ'])


def devowelize(char: str) -> str:
    """
    Maps a Ge'ez character to its 1st order (consonant base).
    
    Args:
        char: The input Ge'ez character.
        
    Returns:
        The 1st order character (base consonant).
    """
    return DEVOWELIZATION_MAP.get(char, char)


def get_char_order(char: str) -> int:
    """
    Returns the order (1-7) of a Ge'ez character.
    
    Args:
        char: The input Ge'ez character.
        
    Returns:
        The order (1-7), or 0 if not found.
    """
    return ORDER_MAP.get(char, 0)


def get_char_by_order(base: str, order: int) -> str:
    """
    Returns the character for a given base consonant and order.
    
    Args:
        base: The base consonant (1st order).
        order: The target order (1-7).
        
    Returns:
        The character at the specified order, or base if not found.
    """
    return REVOWELIZATION_MAP.get((base, order), base)


def get_consonant_skeleton(word: str) -> str:
    """
    Converts a word into its consonant skeleton (1st order sequence).
    
    Args:
        word: The input Ge'ez word.
        
    Returns:
        The sequence of 1st order characters.
    """
    return "".join([devowelize(c) for c in word])


# Laryngeal consonants (gutturals) that affect conjugation patterns
# Base laryngeal consonants (1st order only - devowelize handles all 7 orders)
LARYNGEALS = {'ሀ', 'ሐ', 'ኀ', 'አ', 'ዐ'}

# Weak consonants (for hollow verb detection)
WEAK_CONSONANTS = {'ወ', 'የ'}


def get_radical_vowels(stem: str) -> dict:
    """
    Extracts the vowel orders of each radical in a stem.
    
    Args:
        stem: The verb stem (after prefix stripping).
        
    Returns:
        Dictionary with C1, C2, C3, C4 vowel orders.
    """
    result = {}
    for i, char in enumerate(stem):
        order = get_char_order(char)
        if i == 0:
            result['C1'] = order
        elif i == 1:
            result['C2'] = order
        elif i == 2:
            result['C3'] = order
        elif i == 3:
            result['C4'] = order
    return result


def detect_verb_home(skeleton: str, source_stem: str) -> dict:
    """
    Detects the verb class (Home) algorithmically from vowel patterns.
    
    Algorithm:
    1. Count radicals: 4 = Quadriliteral, 3 = proceed to vowel check
    2. Check C1 vowel order:
       - 5th order (ሀምስ) = Type B (ቀደሰ)
       - 4th order (ራብዕ) = Type C (ባረከ)
       - 7th order (ሳብዕ) = Type C variant (ጦመረ)
       - Otherwise = Type A (default)
    
    Args:
        skeleton: The consonant skeleton (1st order sequence).
        source_stem: The original stem with vowels intact.
        
    Returns:
        Dictionary with 'type', 'confidence', and 'evidence'.
    """
    radical_count = len(skeleton)
    vowels = get_radical_vowels(source_stem)
    c1_order = vowels.get('C1', 1)
    c2_order = vowels.get('C2', 1)
    
    
    # Check for laryngeal consonants in any radical position
    has_laryngeal = False
    laryngeal_positions = []
    for i, char in enumerate(skeleton):
        char_base = devowelize(char)
        if char_base in LARYNGEALS:
            has_laryngeal = True
            position = ['C1', 'C2', 'C3', 'C4'][i] if i < 4 else f'C{i+1}'
            laryngeal_positions.append(f'{position}={char_base}')
    
    # Check for weak consonants (hollow verbs) at C2
    is_hollow = False
    hollow_type = None
    if len(skeleton) >= 2:
        c2_base = devowelize(skeleton[1])
        if c2_base in WEAK_CONSONANTS:
            is_hollow = True
            hollow_type = 'hollow_w' if c2_base == 'ወ' else 'hollow_y'
    
    # === Type Detection (Class) ===
    
    # Rule 1: Radical Count - Quadriliterals
    if radical_count == 4:
        if c2_order == 6:
            return _build_home_result(
                'type_tanbala', 0.95, '4 radicals + C2 is 6th order (ተንበለ)',
                radical_count, has_laryngeal, laryngeal_positions, is_hollow, hollow_type
            )
        else:
            return _build_home_result(
                'type_mahräka', 0.90, '4 radicals (quadriliteral - ማሕረከ)',
                radical_count, has_laryngeal, laryngeal_positions, is_hollow, hollow_type
            )
    
    if radical_count != 3:
        return _build_home_result(
            'type_a', 0.5, f'Unusual radical count: {radical_count}',
            radical_count, has_laryngeal, laryngeal_positions, is_hollow, hollow_type
        )
    
    # Rule 2: C1 Vowel Analysis for 3-radical roots
    
    # 5th order C1 = Type B (ቀደሰ) - e.g., ይቄድስ, ይፌድል
    if c1_order == 5:
        return _build_home_result(
            'type_b', 0.95, 'C1 is 5th order (ሀምስ) → Type B',
            3, has_laryngeal, laryngeal_positions, is_hollow, hollow_type
        )
    
    # 4th order C1 = Type C (ባረከ) - e.g., ይባርክ, ባረከ
    if c1_order == 4:
        return _build_home_result(
            'type_c', 0.95, 'C1 is 4th order (ራብዕ) → Type C',
            3, has_laryngeal, laryngeal_positions, is_hollow, hollow_type
        )
    
    # 7th order C1 = Type C variant (ጦመረ) - e.g., ይጦምር, ጦመረ
    if c1_order == 7:
        return _build_home_result(
            'type_c_o', 0.95, 'C1 is 7th order (ሳብዕ) → Type C-O',
            3, has_laryngeal, laryngeal_positions, is_hollow, hollow_type
        )
    
    # Default: Type A (most common)
    return _build_home_result(
        'type_a', 0.80, f'Default (C1 is {c1_order}th order) → Type A',
        3, has_laryngeal, laryngeal_positions, is_hollow, hollow_type
    )


def _build_home_result(verb_type: str, confidence: float, evidence: str,
                       radical_count: int, has_laryngeal: bool, 
                       laryngeal_positions: list, is_hollow: bool,
                       hollow_type: str) -> dict:
    """
    Build standardized verb home detection result with features.
    
    Separates the verb CLASS (A, B, C, etc.) from FEATURES (laryngeal, hollow).
    This allows the conjugator to use the class template while applying
    feature-specific vowel shifting rules.
    """
    result = {
        'type': verb_type,
        'confidence': confidence,
        'evidence': evidence,
        'radical_count': radical_count,
        'features': {
            'has_laryngeal': has_laryngeal,
            'is_hollow': is_hollow
        }
    }
    
    if has_laryngeal:
        result['features']['laryngeal_positions'] = laryngeal_positions
        
    if is_hollow:
        result['features']['hollow_type'] = hollow_type
        
    return result
