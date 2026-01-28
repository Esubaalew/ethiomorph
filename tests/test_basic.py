import sys
import os

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.normalizer import normalize_geez
from src.decomposer import devowelize, get_consonant_skeleton

def test_normalization():
    print("Testing Normalization...")
    # Test case from user plan
    input_word = "ፀሐይ"
    expected = "ጸሀይ"
    result = normalize_geez(input_word)
    print(f"Input: {input_word}, Expected: {expected}, Got: {result}")
    assert result == expected
    print("Normalization Test Passed!")

def test_devowelization():
    print("\nTesting De-vowelization...")
    # Test case from user plan
    chars = ['ቁ', 'ቂ', 'ቃ', 'ቄ', 'ቅ', 'ቆ']
    expected = 'ቀ'
    for char in chars:
        result = devowelize(char)
        print(f"Input: {char}, Expected: {expected}, Got: {result}")
        assert result == expected
    print("De-vowelization Test Passed!")

def test_combined_flow():
    print("\nTesting Combined Flow (Normalize -> Skeleton)...")
    # Example: ሐውጸነ -> Normalize(ሀውጸነ) -> Skeleton(ሀወጸነ)
    input_word = "ሐውጸነ"
    normalized = normalize_geez(input_word)
    skeleton = get_consonant_skeleton(normalized)
    
    print(f"Input: {input_word}")
    print(f"Normalized: {normalized}")
    print(f"Skeleton: {skeleton}")
    
    assert normalized == "ሀውጸነ"
    assert skeleton == "ሀወጸነ"
    print("Combined Flow Test Passed!")

if __name__ == "__main__":
    test_normalization()
    test_devowelization()
    test_combined_flow()
