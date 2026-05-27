import httpx
import base64
import os
import json
from typing import Optional, Dict, Any, List

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
MODEL_NAME = "llava:7b"
TIMEOUT_SECONDS = 120

SYSTEM_PROMPT = """You are a professional nutrition analysis AI.

Your job:

* Identify foods from image and/or user text
* Estimate realistic portion sizes
* Calculate calories, protein, carbs, and fat

Rules:

* Be conservative with calorie estimates
* If unsure, assume average serving size
* Combine image + text if both exist
* Do NOT explain reasoning
* Output ONLY valid JSON

Return format:
{
"foods": [
{
"name": string,
"portion": string,
"calories": number,
"protein": number,
"carbs": number,
"fat": number
}
],
"total_calories": number,
"confidence": number
}"""

# Default fallback values for nutrients if Ollama misses them
DEFAULT_NUTRIENT_VALUES = {
    "calories": 200,
    "protein": 10,
    "carbs": 20,
    "fat": 10,
}

async def analyze_meal(image_bytes: Optional[bytes] = None, user_text: Optional[str] = None) -> Dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    payload: Dict[str, Any] = {
        "model": MODEL_NAME,
        "stream": False,
        "system": SYSTEM_PROMPT,
        "options": {"temperature": 0.0},
    }

    messages: List[Dict[str, Any]] = []

    # Prepare user message content
    user_message_content: List[Dict[str, Any]] = []

    if user_text:
        user_message_content.append({"type": "text", "text": user_text})

    if image_bytes:
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
        user_message_content.append({"type": "image", "image": encoded_image})

    if user_message_content:
        messages.append({"role": "user", "content": user_message_content})

    payload["messages"] = messages

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                headers=headers,
                json=payload,
                timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            ollama_response = response.json()
            
            # Extract content from the last assistant message
            assistant_message_content = ""
            if "messages" in ollama_response and ollama_response["messages"]:
                for msg in reversed(ollama_response["messages"]):
                    if msg.get("role") == "assistant" and "content" in msg:
                        assistant_message_content = msg["content"]
                        break
            
            if not assistant_message_content:
                return {
                    "error": "Ollama response did not contain assistant message content.",
                    "raw_response": ollama_response,
                    "is_json_valid": False
                }

            # Attempt to parse the content as JSON
            try:
                json_response = json.loads(assistant_message_content)
                # Apply fallback for missing nutrients
                if "foods" in json_response and isinstance(json_response["foods"], list):
                    for food in json_response["foods"]:
                        for nutrient, default_value in DEFAULT_NUTRIENT_VALUES.items():
                            if nutrient not in food or not isinstance(food[nutrient], (int, float)):
                                food[nutrient] = default_value
                return json_response
            except json.JSONDecodeError:
                return {
                    "error": "Ollama response is not valid JSON.",
                    "raw_response": assistant_message_content,
                    "is_json_valid": False
                }

    except httpx.RequestError as exc:
        return {
            "error": f"An error occurred while requesting Ollama: {exc}",
            "is_json_valid": False
        }
    except httpx.HTTPStatusError as exc:
        return {
            "error": f"HTTP error occurred from Ollama: {exc.response.status_code} - {exc.response.text}",
            "is_json_valid": False
        }
    except Exception as exc:
        return {
            "error": f"An unexpected error occurred: {exc}",
            "is_json_valid": False
        }
