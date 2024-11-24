"""
Targets service for managing exercise targets and goals
"""
from datetime import datetime, date
from typing import List, Optional
from api.services.database import DatabaseService
from api.services.exercise import exercise_service
from api.models.target import Target, TargetProgress


class TargetsService:
    """Service for managing exercise targets"""

    def __init__(self):
        """Initialize targets service"""
        self.db = DatabaseService()

    async def get_targets(self, active_only: bool = True) -> List[Target]:
        """Get all targets"""
        query = """
            SELECT * FROM exercise_targets 
            WHERE user_id = (SELECT id FROM users LIMIT 1)
        """

        if active_only:
            query += " AND (end_date IS NULL OR end_date >= CURRENT_DATE)"

        query += " ORDER BY start_date DESC"

        results = self.db.execute_query(query)
        return [Target(**row) for row in results]

    async def create_target(self, target: Target) -> Target:
        """Create a new target"""
        query = """
            INSERT INTO exercise_targets 
                (user_id, type, value, start_date, end_date)
            VALUES (
                (SELECT id FROM users LIMIT 1),
                %s, %s, %s, %s
            )
            RETURNING *
        """
        params = (
            target.type,
            target.value,
            target.start_date or date.today(),
            target.end_date
        )

        result = self.db.execute_query(query, params)
        return Target(**result[0])

    async def update_target(self, target_id: int, data: dict) -> Target:
        """Update an existing target"""
        valid_fields = ['value', 'end_date']
        updates = {k: v for k, v in data.items() if k in valid_fields}

        if not updates:
            raise ValueError("No valid fields to update")

        set_clause = ', '.join(f"{k} = %s" for k in updates)
        query = f"""
            UPDATE exercise_targets 
            SET {set_clause}
            WHERE id = %s 
            AND user_id = (SELECT id FROM users LIMIT 1)
            RETURNING *
        """

        params = tuple(updates.values()) + (target_id,)
        result = self.db.execute_query(query, params)

        if not result:
            raise ValueError("Target not found")

        return Target(**result[0])

    async def delete_target(self, target_id: int) -> None:
        """Delete a target"""
        query = """
            DELETE FROM exercise_targets 
            WHERE id = %s 
            AND user_id = (SELECT id FROM users LIMIT 1)
        """
        self.db.execute_query(query, (target_id,), fetch=False)

    async def get_target_progress(
            self,
            target_id: int
    ) -> Optional[TargetProgress]:
        """Get progress for a specific target"""
        # First get the target
        query = """
            SELECT * FROM exercise_targets 
            WHERE id = %s AND user_id = (SELECT id FROM users LIMIT 1)
        """
        result = self.db.execute_query(query, (target_id,))

        if not result:
            return None

        target = Target(**result[0])

        # Then get the progress
        start_date = target.start_date or date.today()
        end_date = target.end_date or date.today()

        # Calculate progress based on target type
        query = """
            SELECT 
                COALESCE(SUM(duration_seconds), 0) as total_duration,
                COALESCE(SUM(distance_km), 0) as total_distance,
                COALESCE(SUM(steps), 0) as total_steps,
                COALESCE(SUM(calories), 0) as total_calories
            FROM exercise_sessions
            WHERE user_id = (SELECT id FROM users LIMIT 1)
            AND DATE(start_time) BETWEEN %s AND %s
        """
        stats = self.db.execute_query(query, (start_date, end_date))[0]

        # Get the current value based on target type
        current_value = {
            'duration': stats['total_duration'] / 60,  # Convert to minutes
            'distance': stats['total_distance'],
            'steps': stats['total_steps'],
            'calories': stats['total_calories']
        }[target.type]

        progress = (current_value / target.value) * 100 if target.value else 0

        return TargetProgress(
            target=target,
            current_value=current_value,
            progress=min(100, progress),
            completed=progress >= 100
        )

    async def get_all_targets_progress(self) -> List[TargetProgress]:
        """Get progress for all active targets"""
        active_targets = await self.get_targets(active_only=True)
        progress = []

        for target in active_targets:
            target_progress = await self.get_target_progress(target.id)
            if target_progress:
                progress.append(target_progress)

        return progress


# Create singleton instance
targets_service = TargetsService()
