#!/usr/bin/env python3
"""
Seed Data Script — Populate the database with realistic sample data.

Usage:
    cd backend
    python -m scripts.seed_data

Creates:
    - 1 demo user (shreya@example.com / DemoPass123)
    - 5 habits (Water, Sleep, Exercise, Mood, Reading)
    - 30 days of realistic log data with patterns
    - Notification settings

This gives you a working app with data for charts, streaks, and AI context.
"""

import asyncio
import random
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add parent to path so we can import app modules
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import get_settings
from app.database import Base
from app.modules.auth.models import User
from app.modules.auth.security import hash_password
from app.modules.habits.models import Habit
from app.modules.logs.models import HabitLog
from app.modules.notifications.models import NotificationSettings

settings = get_settings()


# ── Demo User ──
DEMO_USER = {
    "email": "shreya@example.com",
    "password": "DemoPass123",
    "full_name": "Shreya",
    "timezone": "Asia/Kolkata",
}

# ── Demo Habits ──
DEMO_HABITS = [
    {"name": "Water Intake", "habit_type": "numeric", "unit": "glasses", "target_value": 8.0, "color": "#3B82F6", "icon": "💧"},
    {"name": "Sleep Hours", "habit_type": "numeric", "unit": "hours", "target_value": 7.5, "color": "#8B5CF6", "icon": "😴"},
    {"name": "Exercise", "habit_type": "boolean", "unit": "", "target_value": None, "color": "#10B981", "icon": "🏃"},
    {"name": "Mood", "habit_type": "scale", "unit": "", "target_value": None, "color": "#F59E0B", "icon": "😊"},
    {"name": "Reading", "habit_type": "numeric", "unit": "minutes", "target_value": 30.0, "color": "#EC4899", "icon": "📖"},
]


def generate_realistic_value(habit: dict, day_of_week: int, day_offset: int) -> dict:
    """Generate realistic habit values with patterns."""
    ht = habit["habit_type"]

    if habit["name"] == "Water Intake":
        # More water on weekdays, less on weekends
        base = 7 if day_of_week < 5 else 5
        value = max(2, min(12, base + random.gauss(0, 1.5)))
        return {"value_numeric": round(value, 1)}

    elif habit["name"] == "Sleep Hours":
        # More sleep on weekends, less on weekdays
        base = 6.5 if day_of_week < 5 else 8.0
        value = max(3, min(11, base + random.gauss(0, 0.8)))
        return {"value_numeric": round(value, 1)}

    elif habit["name"] == "Exercise":
        # Exercise ~5 days/week, skip some weekdays
        did_exercise = random.random() < (0.7 if day_of_week < 5 else 0.5)
        return {"value_boolean": did_exercise}

    elif habit["name"] == "Mood":
        # Mood correlates with sleep (higher sleep → higher mood)
        base = 6 if day_of_week < 5 else 7
        value = max(1, min(10, base + random.randint(-2, 2)))
        return {"value_scale": value}

    elif habit["name"] == "Reading":
        # More reading on weekends
        base = 20 if day_of_week < 5 else 40
        value = max(0, min(120, base + random.gauss(0, 10)))
        return {"value_numeric": round(value)}

    return {}


async def seed():
    """Run the seed script."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Check if demo user already exists
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.email == DEMO_USER["email"]))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"⚠️  Demo user already exists: {DEMO_USER['email']}")
            print("   Delete the user first if you want to re-seed.")
            return

        # Create user
        user_id = uuid4()
        user = User(
            id=user_id,
            email=DEMO_USER["email"],
            password_hash=hash_password(DEMO_USER["password"]),
            full_name=DEMO_USER["full_name"],
            timezone=DEMO_USER["timezone"],
        )
        session.add(user)
        print(f"✅ Created user: {DEMO_USER['email']} (password: {DEMO_USER['password']})")

        # Create habits
        habit_objects = []
        for i, habit_data in enumerate(DEMO_HABITS):
            habit = Habit(
                id=uuid4(),
                user_id=user_id,
                sort_order=i,
                **habit_data,
            )
            session.add(habit)
            habit_objects.append(habit)
            print(f"   ✅ Created habit: {habit_data['icon']} {habit_data['name']}")

        # Create 30 days of logs
        today = date.today()
        log_count = 0

        for day_offset in range(30):
            log_date = today - timedelta(days=29 - day_offset)
            day_of_week = log_date.weekday()

            for habit in habit_objects:
                # Skip some days randomly (85% logging rate)
                if random.random() > 0.85:
                    continue

                habit_dict = {
                    "name": habit.name,
                    "habit_type": habit.habit_type,
                }
                values = generate_realistic_value(habit_dict, day_of_week, day_offset)

                log = HabitLog(
                    id=uuid4(),
                    user_id=user_id,
                    habit_id=habit.id,
                    log_date=log_date,
                    **values,
                )
                session.add(log)
                log_count += 1

        # Create notification settings
        notif = NotificationSettings(user_id=user_id)
        session.add(notif)

        await session.commit()

        print(f"\n🎉 Seed complete!")
        print(f"   📊 {log_count} log entries across 30 days")
        print(f"   🔑 Login: {DEMO_USER['email']} / {DEMO_USER['password']}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
