import httpx
import base64
from typing import Optional

# CHANGE THIS to your server IP (NOT docker bridge unless you KNOW it works)
OLLAMA_URL = "http://192.168.68.67:11434/api/generate"
MODEL_NAME = "llava:7b"


def encode_image(image_bytes: bytes) -> str:
    """Convert image bytes to base64 for Ollama vision models (if used)."""
    return base64.b64encode(image_bytes).decode("utf-8")


async def analyze_meal(
    image_bytes: Optional[bytes] = None,
    user_text: Optional[str] = None
):
    """
    Sends meal data to Ollama and returns structured analysis.
    """

    if not image_bytes and not user_text:
        return {
            "error": "No input provided (image or text required)",
            "is_json_valid": False
        }

    # ----------------------------
    # Build prompt
    # ----------------------------
    prompt = """
You are a nutrition analysis engine.

Your task is to analyze the provided input (text description and/or image description) and return structured nutrition data.

STRICT RULES:
- Return ONLY valid JSON
- Do NOT include markdown (no ``` or formatting)
- Do NOT include explanations or extra text
- Do NOT wrap output in code blocks
- Output must be parsable by json.loads()
- If unsure, make a reasonable estimate rather than failing

INPUT:
You will receive either:
- A description of food eaten (text)
- Or a description of an image of food
- Or both

TASK:
Identify all foods and estimate calories.

OUTPUT FORMAT (MUST FOLLOW EXACTLY):

{
  "foods": [
    {
      "name": "food name",
      "calories": number
    }
  ],
  "total_calories": number,
  "summary": "short 1 sentence summary of the meal"
}

RULES FOR VALUES:
- "foods.name" must be simple (e.g., "apple", "chicken sandwich")
- "calories" must be a numeric estimate
- "total_calories" must equal sum of all foods
- "summary" must be 1 sentence max

NOW ANALYZE THIS INPUT:
{{INPUT}}
"""

    if user_text:
        prompt += f"\nUser input: {user_text}"

    # If you later use vision models:
    image_base64 = encode_image(image_bytes) if image_bytes else None

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }

    # NOTE: Ollama standard /generate does NOT accept images unless using vision models.
    # So we only include text unless you're using llama3.2-vision / llava.
    if image_base64:
        payload["images"] = [image_base64]

    # ----------------------------
    # Request Ollama safely
    # ----------------------------
    try:
        timeout = httpx.Timeout(120.0, connect=10.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(OLLAMA_URL, json=payload)

        response.raise_for_status()
        data = response.json()

        # Ollama returns: { "response": "...", ... }
        raw_text = data.get("response", "")

        # Try JSON parsing from model output
        import json
        try:
            parsed = json.loads(raw_text)
            return parsed
        except Exception:
            return {
                "error": "Model did not return valid JSON",
                "raw_response": raw_text,
                "is_json_valid": False
            }

    except httpx.ConnectError:
        return {
            "error": "Cannot connect to Ollama server (check IP/port/firewall)",
            "is_json_valid": False
        }

    except httpx.TimeoutException:
        return {
            "error": "Ollama request timed out",
            "is_json_valid": False
        }

    except Exception as e:
        return {
            "error": f"Ollama request failed: {str(e)}",
            "is_json_valid": False
        }
