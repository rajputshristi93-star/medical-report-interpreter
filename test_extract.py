from extractor import extract_text, looks_scanned

text = extract_text("samples/cbc_normal.pdf")
print(text)
print("\nScanned?", looks_scanned(text))