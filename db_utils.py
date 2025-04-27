# db_utils.py
import psycopg2
import pandas as pd
from config import DB_CONFIG

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def fetch_data(query, params=None):
    """Fetches data from the database using a pandas DataFrame."""
    conn = get_db_connection()
    if conn:
        try:
            df = pd.read_sql_query(query, conn, params=params)
            return df
        except Exception as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame() # Return empty DataFrame on error
        finally:
            conn.close()
    return pd.DataFrame()

def execute_query(query, params=None):
    """Executes an INSERT, UPDATE, or DELETE query."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            print(f"Error executing query: {e}")
            conn.rollback() # Rollback changes on error
            return False
        finally:
            conn.close()
    return False

# --- Specific Functions ---

def get_db_tables():
    """Fetches list of database tables for dropdown."""
    query = "SELECT table_id, schema_name || '.' || table_name as full_name FROM DatabaseTables ORDER BY schema_name, table_name;"
    df = fetch_data(query)
    # Convert to format suitable for dcc.Dropdown options
    return [{'label': row['full_name'], 'value': row['table_id']} for index, row in df.iterrows()]

def get_access_roles():
    """Fetches list of access roles for dropdown."""
    query = "SELECT role_id, role_name FROM AccessRoles ORDER BY role_id;"
    df = fetch_data(query)
    return [{'label': row['role_name'], 'value': row['role_id']} for index, row in df.iterrows()]

def submit_new_request(requester_id, table_id, role_id, justification, manager_id):
    """Submits a new access request."""
    if not all([requester_id, table_id, role_id, justification, manager_id]):
        print("Error: Missing required fields for submission.")
        return False
    query = """
        INSERT INTO AccessRequests (requester_id, table_id, requested_role_id, justification, status, approver_id)
        VALUES (%s, %s, %s, %s, 'Pending', %s);
    """
    return execute_query(query, (requester_id, table_id, role_id, justification, manager_id))

def get_my_requests(employee_id):
    """Fetches requests submitted by a specific employee."""
    query = """
        SELECT
            ar.request_id,
            dt.schema_name || '.' || dt.table_name AS table_name,
            acr.role_name AS requested_role,
            ar.justification,
            ar.status,
            TO_CHAR(ar.request_date, 'YYYY-MM-DD HH24:MI') AS request_date,
            COALESCE(e_app.first_name || ' ' || e_app.last_name, '') AS approver_name,
            TO_CHAR(ar.decision_date, 'YYYY-MM-DD HH24:MI') AS decision_date,
            ar.approver_comments
        FROM AccessRequests ar
        JOIN DatabaseTables dt ON ar.table_id = dt.table_id
        JOIN AccessRoles acr ON ar.requested_role_id = acr.role_id
        LEFT JOIN Employees e_app ON ar.approver_id = e_app.employee_id
        WHERE ar.requester_id = %s
        ORDER BY ar.request_date DESC;
    """
    return fetch_data(query, (employee_id,))

def get_pending_approvals(manager_id):
    """Fetches requests pending approval for a specific manager."""
    query = """
        SELECT
            ar.request_id,
            e_req.first_name || ' ' || e_req.last_name AS requester_name,
            dt.schema_name || '.' || dt.table_name AS table_name,
            acr.role_name AS requested_role,
            ar.justification,
            TO_CHAR(ar.request_date, 'YYYY-MM-DD HH24:MI') AS request_date
        FROM AccessRequests ar
        JOIN Employees e_req ON ar.requester_id = e_req.employee_id
        JOIN DatabaseTables dt ON ar.table_id = dt.table_id
        JOIN AccessRoles acr ON ar.requested_role_id = acr.role_id
        WHERE ar.approver_id = %s AND ar.status = 'Pending'
        ORDER BY ar.request_date ASC;
    """
    return fetch_data(query, (manager_id,))

def get_request_details(request_id):
     """Fetches full details for a single request."""
     query = """
        SELECT
            ar.request_id,
            e_req.first_name || ' ' || e_req.last_name AS requester_name,
            e_req.email AS requester_email,
            e_req.department AS requester_dept,
            dt.schema_name || '.' || dt.table_name AS table_name,
            dt.description AS table_description,
            acr.role_name AS requested_role,
            acr.description AS role_description,
            ar.justification,
            TO_CHAR(ar.request_date, 'YYYY-MM-DD HH24:MI') AS request_date,
            ar.status
        FROM AccessRequests ar
        JOIN Employees e_req ON ar.requester_id = e_req.employee_id
        JOIN DatabaseTables dt ON ar.table_id = dt.table_id
        JOIN AccessRoles acr ON ar.requested_role_id = acr.role_id
        WHERE ar.request_id = %s;
     """
     df = fetch_data(query, (request_id,))
     # Return details as a dictionary if found
     return df.to_dict('records')[0] if not df.empty else None


def update_request_status(request_id, approver_id, new_status, comments):
    """Updates the status of a request (Approve/Reject)."""
    if new_status not in ('Approved', 'Rejected'):
        print(f"Error: Invalid status '{new_status}'")
        return False
    if new_status == 'Rejected' and not comments:
        print("Error: Comments are mandatory for rejection.")
        return False # Enforce comment for rejection

    query = """
        UPDATE AccessRequests
        SET status = %s,
            approver_id = %s, -- Ensure approver ID is set correctly even if request was misrouted?
            decision_date = CURRENT_TIMESTAMP,
            approver_comments = %s
        WHERE request_id = %s AND status = 'Pending'; -- Only update pending requests
    """
    return execute_query(query, (new_status, approver_id, comments, request_id))