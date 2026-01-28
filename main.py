import sys
import json
from src.stemmer import GeezStemmer

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <geez_word>")
        sys.exit(1)
    
    word = sys.argv[1]
    stemmer = GeezStemmer()
    result = stemmer.extract_root(word)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
