
from fastapi import FastAPI, UploadFile, File
from typing import List
from .database import create_tables, get_all_meals, insert_meal

app = FastAPI()

# Mock data for calorie estimation (replace with a more comprehensive database)
CALORIE_DATA = {
    "apple": 95,
    "banana": 105,
    "orange": 62,
    "chicken breast": 165,
    "rice": 130,
    "broccoli": 55,
    "pasta": 131,
    "beef": 250,
    "potato": 77,
    "egg": 155,
}

@app.on_event("startup")
async def startup_event():
    create_tables()

async def detect_food_with_ollama(image_data: bytes) -> List[str]:
    """Mocks sending image to Ollama vision model and returning detected food items."""
    # In a real scenario, this would involve sending the image_data to an Ollama endpoint
    # and parsing its response. For now, we'll return a dummy list.
    print("Mocking Ollama vision model for food detection...")
    # Based on some very basic image analysis (e.g., size), or just a fixed response for now
    if len(image_data) % 2 == 0:
        return ["apple", "rice"]
    else:
        return ["banana", "chicken breast"]

def estimate_calories(food_items: List[str]) -> float:
    """Estimates total calories based on detected food items and CALORIE_DATA."""
    total_calories = 0.0
    for item in food_items:
        total_calories += CALORIE_DATA.get(item.lower(), 0) # Default to 0 if not found
    return total_calories

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Calorie Tracker API"}

@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    image_data = await file.read()
    detected_foods = await detect_food_with_ollama(image_data)
    total_calories = estimate_calories(detected_foods)

    food_items_str = ", ".join(detected_foods)
    insert_meal(food_items_str, total_calories)

    return {
        "filename": file.filename,
        "detected_foods": detected_foods,
        "total_calories": total_calories,
        "message": "Image analyzed and meal saved successfully."
    }

@app.get("/meals")
async def get_meals():
    meals = get_all_meals()
    return [{"id": meal[0], "food_items": meal[1], "total_calories": meal[2], "timestamp": meal[3]} for meal in meals]
