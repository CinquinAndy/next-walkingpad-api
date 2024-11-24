"""
Database service for managing connections and queries
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from api.config.config import Config


class DatabaseService:
    """Database service class"""

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

    @classmethod
    def execute_query(cls, query, params=None, fetch=True):
        """Execute a database query with error handling"""
        connection = None
        try:
            connection = cls.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, params)

            result = None
            if fetch:
                result = cursor.fetchall()

            connection.commit()
            return result

        except Exception as e:
            if connection:
                connection.rollback()
            raise e

        finally:
            if connection:
                connection.close()


