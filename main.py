from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import Optional

from database import create_tables, get_all_meals, insert_meal
from ollama_client import analyze_meal

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    create_tables()


@app.get("/")
async def read_root():
    return {"message": "Welcome to the Calorie Tracker API"}


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

    if isinstance(analysis_result, dict) and "error" in analysis_result:
        if not analysis_result.get("is_json_valid", True):
            return {
                "error": analysis_result["error"],
                "raw_ollama_response": analysis_result.get("raw_response"),
                "is_json_valid": False
            }
        raise HTTPException(status_code=500, detail=analysis_result["error"])

    foods_summary = ", ".join([f["name"] for f in analysis_result.get("foods", [])])
    total_calories = analysis_result.get("total_calories", 0.0)

    if foods_summary or total_calories > 0:
        insert_meal(foods_summary, total_calories)

    return analysis_result


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
