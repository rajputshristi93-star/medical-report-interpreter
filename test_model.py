import time
from google import genai

client = genai.Client(api_key="AQ.Ab8RN6LLysiHoa9C9Xu-wYEyj-K9TwMUXptOLYHWXOrLXXLa-Q")  # same as in list_models.py

for m in ["gemini-2.5-flash", "gemini-flash-latest", "gemini-3.5-flash",
          "gemini-3.1-flash-lite", "gemini-3.8-flash"]:
    t = time.time()
    try:
        client.models.generate_content(model=m, contents="Say OK")
        print(m, "OK", round(time.time() - t, 1), "s")
    except Exception as e:
        print(m, "FAILED", str(e)[:120])