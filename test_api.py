import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODELS = ["gemini-3.8-flash"]  # add another model name here as a fallback


def ask_llm(prompt, retries=5):
    for attempt in range(retries):
        for model in MODELS:
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                return response.text
            except errors.ServerError as e:  # 503 and other server-side errors
                print(f"{model} busy ({e.code}), retrying...")
        time.sleep(2 ** attempt)  # wait 1s, 2s, 4s, 8s, 16s
    raise RuntimeError("LLM is unavailable right now. Try again later.")


print(ask_llm("Explain what hemoglobin is in one simple sentence."))