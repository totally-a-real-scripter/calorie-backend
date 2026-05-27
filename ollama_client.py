import os
import base64
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://172.17.0.1:11434")


def analyze_meal(image_bytes=None, user_text=None):
    try:
        payload = {
            "model": "llava:7b",
            "prompt": build_prompt(user_text),
            "stream": False
        }

        if image_bytes:
            payload["images"] = [
                base64.b64encode(image_bytes).decode("utf-8")
            ]

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=180
        )

        # 🔥 DEBUG STEP (IMPORTANT)
        if response.status_code != 200:
            return {
                "error": "Ollama returned non-200",
                "status_code": response.status_code,
                "text": response.text
            }

        try:
            data = response.json()
        except Exception as e:
            return {
                "error": "Failed to parse JSON from Ollama",
                "raw": response.text,
                "parse_error": str(e)
            }

        # Ollama returns result in "response"
        return parse_response(data.get("response", ""))

    except Exception as e:
        return {
            "error": "Request to Ollama failed",
            "details": repr(e)
        }


def build_prompt(user_text):
    return f"""
You are a nutrition AI.

Return ONLY valid JSON:

{{
  "foods": [],
  "total_calories": 0,
  "confidence": 0.0
}}

User input:
{user_text}
"""


def parse_response(text):
    return {
        "raw_text": text,
        "parsed": text
    }
