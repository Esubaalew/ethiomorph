#!/usr/bin/env python3
"""
Download full ግስ ከሀ-ፐ from an open Scribd tab via browser CDP extraction.

Prerequisites:
  1. Open https://www.scribd.com/document/747503683 in Cursor browser
  2. Run this script with instructions, OR use the browser automation flow below

This script processes CDP base64 output saved from browser evaluate.
For interactive re-download, scroll the Scribd viewer to load all 34 pages first.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "sources" / "giss_keha_pe_raw.json"
PAGES_DIR = ROOT / "data" / "sources" / "giss_keha_pe_pages"
PDF_PATH = ROOT / "data" / "sources" / "giss_keha_pe.pdf"
VENV_PYTHON = ROOT / ".venv-giss" / "bin" / "python3"


def save_from_cdp_file(cdp_json: Path) -> dict:
    raw = json.loads(cdp_json.read_text())
    value = raw["result"]["value"]
    return json.loads(base64.b64decode(value).decode("utf-8"))


def write_outputs(payload: dict) -> None:
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    pages = payload["pages"]

    token = None
    for p in pages:
        img = p.get("image") or ""
        if "token=" in img:
            token = img.split("token=", 1)[1]
            break

    for p in pages:
        img = p.get("image")
        if not img:
            continue
        url = img if "token=" in img else f"{img}?token={token}" if token else img
        out = PAGES_DIR / f"page_{p['page']:02d}.jpg"
        subprocess.run(["curl", "-sL", url, "-o", str(out)], check=True)

    raw_payload = {
        "source": "scribd",
        "url": "https://www.scribd.com/document/747503683",
        "title": "ግስ ከሀ-ፐ",
        "author": "Ermias Gashu",
        "totalPages": payload["totalPages"],
        "pageTexts": [{"page": p["page"], "text": p["text"], "len": p["textLen"]} for p in pages],
        "imageUrls": [p["image"] for p in pages if p.get("image")],
    }
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PATH.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if VENV_PYTHON.exists():
        import img2pdf  # noqa: F401 — only if venv exists

        imgs = sorted(PAGES_DIR.glob("page_*.jpg"))
        with open(PDF_PATH, "wb") as f:
            f.write(__import__("img2pdf").convert([str(i) for i in imgs]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cdp-json", type=Path, help="CDP Runtime.evaluate output JSON file")
    args = parser.parse_args()
    if not args.cdp_json:
        print("Open Scribd doc in browser, scroll all pages, then extract via CDP.")
        print("Pass --cdp-json path/to/cdp-response.json to process saved extraction.")
        return
    payload = save_from_cdp_file(args.cdp_json)
    write_outputs(payload)
    print(f"Saved {RAW_PATH} ({payload['totalPages']} pages)")


if __name__ == "__main__":
    main()
