import httpx
import base64
from typing import Optional

# CHANGE THIS to your server IP (NOT docker bridge unless you KNOW it works)
OLLAMA_URL = "http://HOST_IP:11434/api/generate"
MODEL_NAME = "llama3"


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
You are a nutrition analysis AI.

Return ONLY valid JSON in this format:
{
  "foods": [{"name": "", "calories": 0}],
  "total_calories": 0,
  "summary": ""
}

Be accurate and conservative with calorie estimates.
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
