"""
Database service for managing connections and queries
"""

import psycopg2
from psycopg2.extras import RealDictCursor

from api.config.config import Config
from api.utils.logger import logger


class DatabaseService:
    """Database service class"""

    def __init__(self):
        """Initialize database connection"""
        try:
            self.conn = self.get_connection()
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def execute_query(self, query: str, params=None):
        """Execute a database query"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    logger.debug(f"Executing query: {query}")
                    logger.debug(f"With parameters: {params}")
                    cur.execute(query, params)

                    if query.strip().upper().startswith('SELECT') or 'RETURNING' in query.upper():
                        result = cur.fetchall()
                        logger.debug(f"Query result: {result}")
                        return result

                    conn.commit()
                    if 'RETURNING' in query.upper():
                        result = cur.fetchall()
                        logger.debug(f"Insert/Update result: {result}")
                        return result
                    return None
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            raise

    def initialize_db(self):
        """Initialize database with default data"""
        try:
            # Create default user if not exists
            query = """
                INSERT INTO users (id, first_name, last_name, email, height_cm, weight_kg, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """
            self.execute_query(
                query,
                (1, 'John', 'Doe', 'john.doe@example.com', 180, 80))

            # Verify user was created
            verify_query = "SELECT id FROM users WHERE id = 1"
            result = self.execute_query(verify_query)

            if result:
                logger.info("Database initialized with default user")
            else:
                logger.warning("Failed to verify default user creation")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    @staticmethod
    def get_connection():
        """Create and return a database connection"""
        db_config = Config.get_database_config()
        if not db_config.get('host'):
            raise ValueError("Database configuration not found")

        return psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            dbname=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password'],
            cursor_factory=RealDictCursor
        )

    def __del__(self):
        """Close database connection when object is destroyed"""
        if hasattr(self, 'conn'):
            self.conn.close()
