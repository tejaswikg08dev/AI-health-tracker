# ============================================================================
# Export — CSV Generator
# ============================================================================
# WHAT THIS FILE DOES:
#   Generates CSV files from habit log data.
#   Uses Python's csv module + io.StringIO for in-memory generation.
#
# WHY IN-MEMORY (not writing to disk):
#   1. Faster — no disk I/O
#   2. Serverless-friendly — Lambda has limited disk space
#   3. Streamable — can send to client before file is fully generated
#   4. No cleanup needed — memory is freed automatically
#
# CSV FORMAT:
#   Date,Habit Name,Type,Value,Unit,Notes
#   2026-09-26,Water Intake,numeric,8.0,glasses,
#   2026-09-26,Exercise,boolean,Yes,,Morning run
#   2026-09-26,Mood,scale,7,,Felt good today
# ============================================================================

import csv
import io
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.habits.repository import HabitRepository
from app.modules.logs.repository import LogRepository
from app.shared.logging import get_logger

logger = get_logger(__name__)


class CsvGenerator:
    """
    Generates CSV exports of habit log data.

    Usage:
        generator = CsvGenerator(session)
        csv_content = await generator.generate(user_id, start_date, end_date)
        # csv_content is a string — write to file, return as response, or upload to S3
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> str:
        """
        Generate a CSV string from habit log data.

        Returns the full CSV as a string (including header row).
        Uses io.StringIO to build the CSV in memory.
        """
        habit_repo = HabitRepository(self.session)
        log_repo = LogRepository(self.session)

        # Fetch data
        habits = await habit_repo.get_user_habits(user_id, include_archived=True)
        logs = await log_repo.get_logs_for_range(user_id, start_date, end_date)

        # Build lookup maps
        habit_map = {str(h.id): h for h in habits}

        # Generate CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow([
            "Date", "Habit Name", "Type", "Value", "Unit", "Notes",
        ])

        # Data rows
        for log in logs:
            habit = habit_map.get(str(log.habit_id))
            if not habit:
                continue

            # Determine value based on type
            if habit.habit_type == "numeric":
                value = log.value_numeric if log.value_numeric is not None else ""
            elif habit.habit_type == "boolean":
                value = "Yes" if log.value_boolean else "No" if log.value_boolean is not None else ""
            elif habit.habit_type == "scale":
                value = log.value_scale if log.value_scale is not None else ""
            else:
                value = ""

            writer.writerow([
                str(log.log_date),
                habit.name,
                habit.habit_type,
                value,
                habit.unit,
                log.notes or "",
            ])

        csv_content = output.getvalue()
        output.close()

        logger.info(
            "csv_generated",
            user_id=str(user_id),
            rows=len(logs),
            date_range=f"{start_date} to {end_date}",
        )

        return csv_content

    async def generate_bytes(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> bytes:
        """Generate CSV as bytes (for S3 upload or file download)."""
        csv_str = await self.generate(user_id, start_date, end_date)
        return csv_str.encode("utf-8")
