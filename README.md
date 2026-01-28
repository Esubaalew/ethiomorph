# EthioMorph

**Ge'ez Morphological Analysis and Generation Engine**

A rule-based morphological system for Classical Ge'ez (ግእዝ) that analyzes words into roots and generates conjugations from roots.

🌐 ** Demo**: [ethiomorph.esubalew.et](https://ethiomorph.esubalew.et)

> ⚠️ **Note**: This is a work-in-progress project. It may have bugs and incomplete features.

## What It Does

**Input a word** → Get the root and grammatical analysis  
**Input a root** → Get the full conjugation table

### Example

```
Analyze: ያስተቃትል → Root: ቀተለ, Stem: Causative-Passive, Tense: Imperfective

Generate: ቀተለ → ቀተለ, ይቀትል, ይትቀተል, ያቀትል, ያስተቃትል...
```

## Supported Verb Types

| Type | Example | Description |
|------|---------|-------------|
| **ቀተለ** | Type A | Strong triradical |
| **ቀደሰ** | Type B | Geminate |
| **ባረከ** | Type C | Long vowel |
| **ጦመረ** | Type C-O | O-initial |
| **ሴሰየ** | Weak | Weak final |
| **ክህለ** | Laryngeal | Has laryngeal consonant |
| **ማሕረከ** | Quad | Quadriliteral |
| **ተንበለ** | T-Quad | ተ- prefixed quad |

## Supported Stems

| Stem | Prefix | Example |
|------|--------|---------|
| I Basic | — | ቀተለ → ይቀትል |
| II Passive | ተ- | ተቀተለ → ይትቀተል |
| III Causative | አ- | አቀተለ → ያቀትል |
| IV Causative-Passive | አስተ- | አስተቀተለ → ያስተቃትል |
| V Reciprocal | ተ- | ተቃታለ → ይትቃታል |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/analyze?word=ያስተቃትል` | Analyze a word |
| `/api/expand?root=ቀተለ` | Generate conjugations |


**Esubalew Chekol**  
Addis Ababa University
