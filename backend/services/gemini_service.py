from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

import json

def generate(prompt: str):
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )
    
    text = response.text.strip()

    try:
        return json.loads(text) 
    except:
        return {"error": "Invalid JSON from AI", "raw": text}