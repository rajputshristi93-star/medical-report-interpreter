import pdfplumber


def extract_text(file) -> str:
    """Accepts a file path or an uploaded file object. Returns the text of all pages."""
    parts = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def looks_scanned(text: str) -> bool:
    """Very little text usually means a scanned image PDF that needs OCR."""
    return len(text) < 50