"""
EthioMorph Normalizer - Homophone Standardization
=================================================
Utilities for normalizing Ge'ez text by mapping homophones to their canonical forms.

Esubalew Chekol
"""

NORMALIZATION_MAP = {
    'ሐ': 'ሀ', 'ሑ': 'ሁ', 'ሒ': 'ሂ', 'ሓ': 'ሃ', 'ሔ': 'ሄ', 'ሕ': 'ህ', 'ሖ': 'ሆ',
    'ኀ': 'ሀ', 'ኁ': 'ሁ', 'ኂ': 'ሂ', 'ኃ': 'ሃ', 'ኄ': 'ሄ', 'ኅ': 'ህ', 'ኆ': 'ሆ',
    'ሠ': 'ሰ', 'ሡ': 'ሱ', 'ሢ': 'ሲ', 'ሣ': 'ሳ', 'ሤ': 'ሴ', 'ሥ': 'ስ', 'ሦ': 'ሶ',
    'ፀ': 'ጸ', 'ፁ': 'ጹ', 'ጺ': 'ጺ', 'ፃ': 'ጻ', 'ፄ': 'ጼ', 'ፅ': 'ጽ', 'ፆ': 'ጾ',
    'ዓ': 'አ', 'ዑ': 'ኡ', 'ዒ': 'ኢ', ' ዓ': 'አ', 'ዔ': 'ኤ', 'ዕ': 'እ', 'ዖ': 'ኦ'
}


def normalize_geez(text: str) -> str:
    """
    Normalizes Ge'ez text by mapping homophones to their canonical forms.
    
    Args:
        text: The input Ge'ez text.
        
    Returns:
        The normalized text.
    """
    return "".join([NORMALIZATION_MAP.get(char, char) for char in text])
