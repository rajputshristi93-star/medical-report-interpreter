import sys
import pandas as pd
from extractor import extract_text
from interpreter import extract_results, explain_results, verify_against_text
from rules import add_status

path = sys.argv[1] if len(sys.argv) > 1 else "samples/cbc_low_hb.pdf"
text = extract_text(path)
results = add_status(verify_against_text(extract_results(text), text))

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
print(pd.DataFrame(results))
print("\n" + explain_results(results))