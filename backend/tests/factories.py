# ============================================================================
# Test Data Factories — Generate Realistic Fake Data
# ============================================================================
# WHY FACTORIES (not hardcoded dicts):
#   1. DRY — define the shape once, generate many variations
#   2. Realistic — random but valid data catches edge cases
#   3. Readable — test_create_habit(habit=HabitFactory()) vs a 15-field dict
# ============================================================================

import random
from datetime import date, timedelta
from uuid import uuid4

from app.types import *  # noqa — not actual imports, just for reference


def make_user_data(overrides: dict | None = None) -> dict:
    """Generate valid user registration data."""
    data = {
        "email": f"user_{uuid4().hex[:8]}@example.com",
        "password": "SecurePass123!",
        "full_name": random.choice(["Shreya", "Arjun", "Priya", "Rahul", "Ananya"]),
        "timezone": random.choice(["UTC", "Asia/Kolkata", "America/New_York"]),
    }
    if overrides:
        data.update(overrides)
    return data


def make_habit_data(overrides: dict | None = None) -> dict:
    """Generate valid habit creation data."""
    templates = [
        {"name": "Water Intake", "habit_type": "numeric", "unit": "glasses", "target_value": 8, "icon": "💧", "color": "#3B82F6"},
        {"name": "Sleep Hours", "habit_type": "numeric", "unit": "hours", "target_value": 7.5, "icon": "😴", "color": "#8B5CF6"},
        {"name": "Exercise", "habit_type": "boolean", "unit": "", "target_value": None, "icon": "🏃", "color": "#10B981"},
        {"name": "Mood", "habit_type": "scale", "unit": "", "target_value": None, "icon": "😊", "color": "#F59E0B"},
        {"name": "Reading", "habit_type": "numeric", "unit": "minutes", "target_value": 30, "icon": "📖", "color": "#EC4899"},
    ]
    data = random.choice(templates).copy()
    # Make name unique to avoid duplicate errors
    data["name"] = f"{data['name']} {uuid4().hex[:4]}"
    if overrides:
        data.update(overrides)
    return data


def make_log_data(habit_id: str, habit_type: str, log_date: str | None = None, overrides: dict | None = None) -> dict:
    """Generate valid log creation data matching the habit type."""
    data: dict = {
        "habit_id": habit_id,
        "log_date": log_date or str(date.today()),
    }

    if habit_type == "numeric":
        data["value_numeric"] = round(random.uniform(1, 10), 1)
    elif habit_type == "boolean":
        data["value_boolean"] = random.choice([True, False])
    elif habit_type == "scale":
        data["value_scale"] = random.randint(1, 10)

    if overrides:
        data.update(overrides)
    return data


def make_bulk_log_data(habits: list[dict], log_date: str | None = None) -> dict:
    """Generate bulk log data for multiple habits."""
    entries = []
    for h in habits:
        entry: dict = {"habit_id": h["id"]}
        if h["habit_type"] == "numeric":
            entry["value_numeric"] = round(random.uniform(1, 10), 1)
        elif h["habit_type"] == "boolean":
            entry["value_boolean"] = True
        elif h["habit_type"] == "scale":
            entry["value_scale"] = random.randint(1, 10)
        entries.append(entry)

    return {
        "log_date": log_date or str(date.today()),
        "entries": entries,
    }
