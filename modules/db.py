# modules/db.py
import psycopg2
import psycopg2.extras # For dictionary cursor

# --- Database Configuration ---
DB_CONFIG = {
    "dbname": "access_request_db",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": "5432"
}

# --- Helper Function for DB Connection ---
def get_db_connection(app): # Added app parameter for logging
    """
    Establishes a connection to the PostgreSQL database.
    Uses app.logger for logging connection attempts.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        app.logger.info("Database connection successful.")
        return conn
    except psycopg2.Error as e:
        app.logger.error(f"Error connecting to PostgreSQL database: {e}")
        return None