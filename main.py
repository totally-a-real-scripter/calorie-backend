from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import Optional

from .database import create_tables, get_all_meals, insert_meal
from .ollama_client import analyze_meal

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    create_tables()


@app.get("/")
async def read_root():
    return {"message": "Meal API running"}


@app.post("/analyze-meal")
async def analyze_meal_endpoint(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = None
):
    if not file and not text:
        raise HTTPException(
            status_code=400,
            detail="Either an image file or text input must be provided."
        )

    image_bytes = None
    if file:
        image_bytes = await file.read()

    analysis_result = await analyze_meal(
        image_bytes=image_bytes,
        user_text=text
    )

    if analysis_result["status"] == "error":
        if not analysis_result["is_json_valid"]:
            return {
                "error": analysis_result["message"],
                "raw_ollama_response": analysis_result.get("raw_ollama_response"),
                "is_json_valid": False
            }
        raise HTTPException(status_code=500, detail=analysis_result["message"])

    # Extract data from the 'data' key in analysis_result
    ollama_data = analysis_result["data"]
    foods_summary = ", ".join([f["name"] for f in ollama_data.get("foods", [])])
    total_calories = ollama_data.get("total_calories", 0.0)

    if foods_summary or total_calories > 0:
        insert_meal(foods_summary, total_calories)

    return ollama_data


@app.get("/meals")
async def get_meals():
    meals = get_all_meals()
    return [
        {
            "id": meal[0],
            "food_items": meal[1],
            "total_calories": meal[2],
            "timestamp": meal[3]
        }
        for meal in meals
    ]
