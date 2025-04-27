# config.py
# IMPORTANT: Use environment variables or a secure method in production!
# For this example, we'll hardcode (not recommended for real apps).
DB_CONFIG = {
    "dbname": "access_request_db", # CHANGE TO YOUR DB NAME
    "user": "your_postgres_user",    # CHANGE TO YOUR USER
    "password": "your_postgres_password", # CHANGE TO YOUR PASSWORD
    "host": "localhost",           # Often localhost
    "port": "5432"                 # Default PostgreSQL port
}

# --- Simulation ---
# For this example, we simulate login without real authentication
# Map user input (like employee ID) to employee details and role
SIMULATED_USERS = {
    "101": {"employee_id": 1, "name": "Alice Wonder", "role": "requestor", "manager_id": 3},
    "102": {"employee_id": 2, "name": "Bob The Builder", "role": "requestor", "manager_id": 3},
    "201": {"employee_id": 3, "name": "Charlie Chaplin (Manager)", "role": "approver", "manager_id": None},
    "103": {"employee_id": 4, "name": "Diana Prince", "role": "requestor", "manager_id": 5},
    "202": {"employee_id": 5, "name": "Edward Scissorhands (Manager)", "role": "approver", "manager_id": None}
}