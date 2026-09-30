import pandas as pd
from extractor import extract_text
from interpreter import extract_results, explain_results
from rules import add_status

text = extract_text("samples/cbc_low_hb.pdf")
results = add_status(extract_results(text))

print(pd.DataFrame(results))
print("\n" + explain_results(results))