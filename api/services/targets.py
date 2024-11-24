"""
Targets service handling
"""
from datetime import date
from typing import List, Optional
from api.services.database import DatabaseService
from api.utils.helpers import parse_date
from api.utils.logger import get_logger
from api.models.target import Target, TargetProgress


logger = get_logger()

class TargetsService:
    def __init__(self):
        """Initialize targets service"""
        self.db = DatabaseService()

    async def get_targets(self, user_id: Optional[int] = None, active_only: bool = True) -> List[Target]:
        """Get all targets for a user"""
        try:
            query = """
                SELECT * FROM exercise_targets
                WHERE 1=1
            """
            params = []

            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)
            else:
                query += " AND user_id = (SELECT id FROM users LIMIT 1)"

            if active_only:
                query += " AND (end_date IS NULL OR end_date >= CURRENT_DATE)"

            query += " ORDER BY start_date DESC"

            logger.debug(f"Executing get_targets query: {query}")
            logger.debug(f"With parameters: {params}")

            results = self.db.execute_query(query, params if params else None)
            return [Target.from_db_row(row) for row in results]
        except Exception as e:
            logger.error(f"Failed to get targets: {e}")
            raise

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
        self.db.execute_query(query, (target_id,))

    async def get_target_progress(self, target_id: int) -> Optional[TargetProgress]:
        """Get progress for a specific target"""
        try:
            # First get the target
            query = """
                SELECT * FROM exercise_targets 
                WHERE id = %s AND user_id = (SELECT id FROM users LIMIT 1)
            """
            result = self.db.execute_query(query, (target_id,))

            if not result:
                logger.warning(f"No target found with id {target_id}")
                return None

            target = Target.from_db_row(result[0])
            logger.debug(f"Found target: {target.to_dict()}")

            # Calculate date range
            start_date = target.start_date
            end_date = target.end_date or date.today()

            # Get exercise stats
            stats_query = """
                SELECT 
                    COALESCE(SUM(duration_seconds), 0) as total_duration,
                    COALESCE(SUM(distance_km), 0) as total_distance,
                    COALESCE(SUM(steps), 0) as total_steps,
                    COALESCE(SUM(calories), 0) as total_calories,
                    MAX(updated_at) as last_updated
                FROM exercise_sessions
                WHERE user_id = (SELECT id FROM users LIMIT 1)
                AND DATE(start_time) BETWEEN %s AND %s
                AND end_time IS NOT NULL
            """
            stats = self.db.execute_query(stats_query, (start_date, end_date))[0]
            logger.debug(f"Exercise stats: {stats}")

            # Map target type to corresponding stat
            type_to_stat = {
                'duration': stats['total_duration'] / 60,  # Convert to minutes
                'distance': stats['total_distance'],
                'steps': stats['total_steps'],
                'calories': stats['total_calories']
            }

            current_value = type_to_stat.get(target.type, 0)
            progress = min(100, (current_value / target.value * 100) if target.value > 0 else 0)
            completed = progress >= 100

            return TargetProgress(
                target=target,
                current_value=current_value,
                progress=progress,
                completed=completed,
                last_updated=stats['last_updated']
            )

        except Exception as e:
            logger.error(f"Error getting target progress: {e}", exc_info=True)
            raise

    async def get_all_targets_progress(self) -> List[TargetProgress]:
        """Get progress for all active targets"""
        active_targets = await self.get_targets(active_only=True)
        progress = []

        for target in active_targets:
            target_progress = await self.get_target_progress(target.id)
            if target_progress:
                progress.append(target_progress)

        return progress

    async def create_target(self, target_data: dict) -> Target:
        """Create a new target"""
        try:
            logger.debug(f"Creating new target with data: {target_data}")

            # Parse dates
            start_date = parse_date(target_data.get('start_date')) or date.today()
            end_date = parse_date(target_data.get('end_date'))

            query = """
                   INSERT INTO exercise_targets 
                   (user_id, type, value, start_date, end_date, completed, created_at)
                   VALUES (
                       (SELECT id FROM users LIMIT 1),
                       %s, %s, %s, %s, %s, NOW()
                   )
                   RETURNING *
               """
            params = (
                target_data['type'],
                float(target_data['value']),
                start_date,
                end_date,
                False  # initial completed status
            )

            logger.debug(f"Executing insert with params: {params}")
            result = self.db.execute_query(query, params)

            if not result:
                raise Exception("Failed to create target")

            return Target.from_db_row(result[0])

        except Exception as e:
            logger.error(f"Failed to create target: {e}")
            raise


# Create singleton instance
targets_service = TargetsService()
