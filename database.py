import sqlite3

DATABASE_URL = "./calorie_tracker.db"

def create_tables():
    with sqlite3.connect(DATABASE_URL) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                food_items TEXT NOT NULL,
                total_calories REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def insert_meal(food_items: str, total_calories: float):
    with sqlite3.connect(DATABASE_URL) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO meals (food_items, total_calories) VALUES (?, ?)",
                       (food_items, total_calories))
        conn.commit()

def get_all_meals():
    with sqlite3.connect(DATABASE_URL) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, food_items, total_calories, timestamp FROM meals")
        return cursor.fetchall()
