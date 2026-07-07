"""
Load ግስ ከሀ-ፐ grammar index for stemmer disambiguation and gloss lookup.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from src.normalizer import normalize_geez
from src.decomposer import get_consonant_skeleton, get_char_order

NOISY_GLOSS_RE = re.compile(r"^.{1,2}$|❖")


def _is_noisy_gloss(gloss: str | None) -> bool:
    if not gloss:
        return True
    return bool(NOISY_GLOSS_RE.match(gloss.strip()))


PATTERN_CODE_MAP = {
    "ቀተ": {"name": "perfective", "geez_name": "ቀዳማይ አንቀጽ", "english_name": "Perfective"},
    "ቀደ": {"name": "perfective_alt", "geez_name": "ቀዳማይ አንቀጽ", "english_name": "Perfective"},
    "ጦመ": {"name": "participle", "geez_name": "ሥራሴ", "english_name": "Participle"},
    "ተን": {"name": "noun_agent", "geez_name": "ስም ፈጣሪ", "english_name": "Agent Noun"},
    "ባረ": {"name": "adjective", "geez_name": "ስም መገለጫ", "english_name": "Adjective"},
    "ማህ": {"name": "adverb", "geez_name": "ግስ መገለጫ", "english_name": "Adverb"},
    "ሴሰ": {"name": "noun", "geez_name": "ስም", "english_name": "Noun"},
    "ርዕስ": {"name": "topic", "geez_name": "ርዕስ", "english_name": "Topic/Heading"},
    "ክህ": {"name": "conjugation_grid", "geez_name": "ክፍል", "english_name": "Conjugation grid"},
}


class GrammarIndex:
    """Lookup over ግስ ከሀ-ፐ plus መጽሐፈ ግስ ዘዋድላ indices."""

    def __init__(self, path: str | Path | None = None, *, secondary_path: str | Path | None = None):
        self.roots: dict[str, dict] = {}
        self.form_to_roots: dict[str, list[str]] = {}
        self.skeleton_to_roots: dict[str, list[str]] = {}
        self.loaded = False
        self.secondary_roots: dict[str, dict] = {}

        data_dir = Path(__file__).resolve().parents[1] / "data"
        if path is None:
            path = data_dir / "grammar_index.json"
        if secondary_path is None:
            secondary_path = data_dir / "grammar_zewadla_index.json"

        path = Path(path)
        secondary_path = Path(secondary_path)

        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            self._ingest_payload(payload, primary=True)
            self.source = {
                "title": payload.get("source"),
                "author": payload.get("author"),
                "url": payload.get("url"),
                "total_pages": payload.get("total_pages"),
            }
            self.loaded = True

        if secondary_path.exists():
            payload = json.loads(secondary_path.read_text(encoding="utf-8"))
            self._ingest_payload(payload, primary=False)
            self.secondary_source = {
                "title": payload.get("source"),
                "url": payload.get("url"),
                "total_pages": payload.get("total_pages"),
            }
            if not self.loaded:
                self.source = self.secondary_source
                self.loaded = True

    def _ingest_payload(self, payload: dict, *, primary: bool) -> None:
        for entry in payload.get("roots", []):
            root = entry["root"]
            if primary:
                self.roots[root] = entry
            else:
                self.secondary_roots[root] = entry
                if root not in self.roots:
                    self.roots[root] = entry
                else:
                    merged = dict(self.roots[root])
                    if _is_noisy_gloss(merged.get("primary_gloss")) and entry.get("primary_gloss"):
                        merged["primary_gloss"] = entry["primary_gloss"]
                    merged_glosses = list(dict.fromkeys(
                        (merged.get("glosses") or []) + (entry.get("glosses") or [])
                    ))
                    merged["glosses"] = merged_glosses[:16]
                    if entry.get("synonyms"):
                        merged["synonyms"] = entry.get("synonyms")
                    self.roots[root] = merged
            skel = normalize_geez(get_consonant_skeleton(root))
            self.skeleton_to_roots.setdefault(skel, [])
            if root not in self.skeleton_to_roots[skel]:
                self.skeleton_to_roots[skel].append(root)

        for form, roots in payload.get("form_to_roots", {}).items():
            existing = self.form_to_roots.setdefault(form, [])
            for root in roots:
                if root not in existing:
                    existing.append(root)
            skel = normalize_geez(get_consonant_skeleton(form))
            for root in roots:
                if root not in self.skeleton_to_roots.get(skel, []):
                    self.skeleton_to_roots.setdefault(skel, []).append(root)

    def get_root(self, root: str) -> dict | None:
        return self.roots.get(root)

    def primary_gloss(self, root: str) -> str | None:
        entry = self.roots.get(root)
        if not entry:
            return None
        gloss = entry.get("primary_gloss")
        if _is_noisy_gloss(gloss):
            alt = self.secondary_roots.get(root)
            if alt and alt.get("primary_gloss"):
                return alt["primary_gloss"]
        return gloss

    def grammar_patterns(self, root: str) -> list[dict]:
        entry = self.roots.get(root)
        if not entry:
            return []
        return [PATTERN_CODE_MAP.get(code, {"name": code}) for code in entry.get("patterns", [])]

    def resolve_skeleton(self, skeleton: str, *, source: str | None = None, pattern_name: str | None = None) -> str | None:
        norm = normalize_geez(get_consonant_skeleton(skeleton))
        candidates = list(dict.fromkeys(self.skeleton_to_roots.get(norm, [])))
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        if source:
            order = get_char_order(source[0])
            if order:
                order_hits = [c for c in candidates if get_char_order(c[0]) == order]
                if len(order_hits) == 1:
                    return order_hits[0]

        if pattern_name in {"imperfective", "jussive"} and source and get_char_order(source[0]) == 6:
            for candidate in candidates:
                gloss = self.primary_gloss(candidate) or ""
                if "እሽኰኰ" in gloss or candidate.startswith("ን"):
                    return candidate

        return candidates[0]

    def lookup_form(self, word: str) -> list[str]:
        if word in self.form_to_roots:
            return self.form_to_roots[word]
        norm = normalize_geez(word)
        hits = []
        for form, roots in self.form_to_roots.items():
            if normalize_geez(form) == norm:
                hits.extend(roots)
        return list(dict.fromkeys(hits))

    def reference(self, root: str) -> dict | None:
        entry = self.roots.get(root)
        if not entry:
            return None
        ref = {
            "source": self.source.get("title"),
            "author": self.source.get("author"),
            "url": self.source.get("url"),
            "pages": entry.get("pages", []),
            "patterns": entry.get("patterns", []),
            "glosses": entry.get("glosses", []),
        }
        alt = self.secondary_roots.get(root)
        if alt:
            ref["secondary_source"] = getattr(self, "secondary_source", {}).get("title")
            ref["secondary_pages"] = alt.get("pages", [])
            if alt.get("synonyms"):
                ref["synonyms"] = alt.get("synonyms")
        return ref
