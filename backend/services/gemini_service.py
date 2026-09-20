from google import genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

def generate(prompt: str):
    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

        text = response.text.strip()
        print("GEMINI RAW RESPONSE:")
        print(text)
        if text.startswith("```json"):
            text = text.replace("```json", "", 1)
            text = text.replace("```", "", 1)
            text = text.strip()

        return json.loads(text)

    except Exception as e:
        print("Gemini error:", e)

        return None
       