import httpx
import base64
import os
import json
import re
from typing import Optional, Dict, Any, List

# Configurable Ollama base URL via environment variable
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.68.67:11434")
MODEL_NAME = "llama3.1:8b" # Updated model name
TIMEOUT_SECONDS = 120 # Minimum 60s, using 120s as a safe default
RETRIES = 2 # At least 2 retries

# Critical system prompt for Ollama
CRITICAL_PROMPT = """You are a professional nutrition analysis AI.
Your job is to identify foods from an image and/or user text, estimate realistic portion sizes, and calculate calories.
You MUST return ONLY valid JSON, with no markdown, no backticks, and no explanation.
If you are unsure about any value, return empty arrays for foods or 0 for numbers.

Return format:
{
  "foods": [
    {
      "name": "string",
      "calories": number
    }
  ],
  "total_calories": number,
  "summary": "string"
}
"""

async def analyze_meal(image_bytes: Optional[bytes] = None, user_text: Optional[str] = None) -> Dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    
    # Construct the full prompt based on image and text presence
    full_prompt = CRITICAL_PROMPT
    if user_text:
        full_prompt += f" User input: {user_text}"

    payload: Dict[str, Any] = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": False,
    }

    # Add image to payload if provided
    if image_bytes:
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
        payload["images"] = [encoded_image]

    # Retry logic for robust communication with Ollama
    for attempt in range(RETRIES + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate", # Updated endpoint
                    headers=headers,
                    json=payload,
                    timeout=TIMEOUT_SECONDS
                )
                response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
                ollama_response = response.json()

                # Ollama's /api/generate response structure contains 'response' key for the actual text
                response_content = ollama_response.get("response", "").strip()

                # Attempt to extract JSON from potentially malformed responses
                # This regex looks for a JSON object and captures it
                json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                
                if json_match:
                    json_string = json_match.group(0)
                    try:
                        json_analysis = json.loads(json_string)
                        # Ensure required fields exist with default fallbacks
                        json_analysis.setdefault("foods", [])
                        json_analysis.setdefault("total_calories", 0)
                        json_analysis.setdefault("summary", "Analysis completed.")
                        
                        # Fallback for missing 'name' or 'calories' in food items
                        for food in json_analysis["foods"]:
                            food.setdefault("name", "unknown food")
                            food.setdefault("calories", 0)

                        return {
                            "status": "success",
                            "data": json_analysis,
                            "raw_ollama_response": response_content,
                            "is_json_valid": True
                        }
                    except json.JSONDecodeError:
                        return {
                            "status": "error",
                            "message": "Ollama response contains invalid JSON.",
                            "raw_ollama_response": response_content,
                            "is_json_valid": False
                        }
                else:
                    return {
                        "status": "error",
                        "message": "Ollama response did not contain a valid JSON object.",
                        "raw_ollama_response": response_content,
                        "is_json_valid": False
                    }

        except httpx.RequestError as exc:
            if attempt < RETRIES:
                print(f"Attempt {attempt + 1} failed: {exc}. Retrying...")
                continue
            return {
                "status": "error",
                "message": f"Failed to connect to Ollama after {RETRIES + 1} attempts: {exc}",
                "is_json_valid": False
            }
        except httpx.HTTPStatusError as exc:
            if attempt < RETRIES:
                print(f"Attempt {attempt + 1} failed with HTTP status {exc.response.status_code}: {exc.response.text}. Retrying...")
                continue
            return {
                "status": "error",
                "message": f"Ollama HTTP error after {RETRIES + 1} attempts: {exc.response.status_code} - {exc.response.text}",
                "is_json_valid": False
            }
        except Exception as exc:
            if attempt < RETRIES:
                print(f"Attempt {attempt + 1} failed with unexpected error: {exc}. Retrying...")
                continue
            return {
                "status": "error",
                "message": f"An unexpected error occurred after {RETRIES + 1} attempts: {exc}",
                "is_json_valid": False
            }
    
    # Should not be reached if retry logic is correct, but as a safeguard
    return {
        "status": "error",
        "message": "Unknown error after all retries.",
        "is_json_valid": False
    }
