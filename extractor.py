import re

import pdfplumber


def extract_text(file) -> str:
    """Accepts a file path or file object. Returns the text of all pages."""
    parts = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def looks_scanned(text: str) -> bool:
    """Very little text usually means a scanned image PDF."""
    return len(text) < 50


def clean_lines(text: str, max_len: int = 170) -> list:
    """Drops paragraph notes, separators and repeated headers so the AI sees mostly result rows."""
    keep, seen = [], set()
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) > max_len:
            continue
        if set(line) <= set("-_=. "):
            continue
        if not (re.search(r"\d", line) or len(line) <= 40):
            continue
        if line in seen:
            continue
        seen.add(line)
        keep.append(line)
    return keep