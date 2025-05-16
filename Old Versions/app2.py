import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ctx, dash_table
import psycopg2
import psycopg2.extras # For dictionary cursor
import logging
from datetime import datetime # For formatting dates

# --- Database Configuration ---
DB_CONFIG = {
    "dbname": "access_request_db",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": "5432"
}

# --- Initialize Dash App ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "GCash DB Access System"

# Configure logging
log_format = '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
app.logger.setLevel(logging.INFO) # Dash's built-in logger

# --- Helper Function for DB Connection ---
def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        app.logger.info("Database connection successful.")
        return conn
    except psycopg2.Error as e:
        app.logger.error(f"Error connecting to PostgreSQL database: {e}")
        return None

# --- Layout Definitions ---

# Login Layout (from your existing code)
login_layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Internal Database Access Request System"), width=12), className="mb-3 mt-5 text-center"),
    dbc.Row(dbc.Col(html.H4("Login"), width=12), className="mb-4 text-center"),
    dbc.Row(
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Please enter your credentials"),
                dbc.CardBody([
                    dbc.Form([
                        html.Div([
                            dbc.Label("Username (Email)", html_for="username-input", className="form-label"),
                            dbc.Input(type="email", id="username-input", placeholder="Enter your email", required=True),
                        ], className="mb-3"),
                        html.Div([
                            dbc.Label("Password", html_for="password-input", className="form-label"),
                            dbc.Input(type="password", id="password-input", placeholder="Enter your password", required=True),
                        ], className="mb-3"),
                        dbc.Button("Login", id="login-button", color="primary", className="w-100 mt-3", n_clicks=0),
                        html.Div(id="login-status-message", className="mt-3 text-center") # Renamed for clarity
                    ])
                ])
            ]),
            width={"size": 6, "offset": 3},
            lg={"size": 4, "offset": 4}
        )
    )
], fluid=True)

# Dashboard Layout
def create_dashboard_layout(session_data):
    if not session_data or not session_data.get('logged_in'):
        return login_layout

    user_first_name = session_data.get('first_name', 'User')
    is_manager = session_data.get('is_manager', False)
    app.logger.info(f"Creating dashboard layout for {user_first_name}, is_manager: {is_manager}")

    my_requests_section = [
        html.H3("My Access Requests", className="mt-4"),
        dash_table.DataTable(
            id='my-requests-table',
            # ... (rest of table props)
        ),
    ]

    approval_section_content = []
    if is_manager:
        app.logger.info(f"User {user_first_name} is a manager. Adding approval section.")
        approval_section_content = [
            html.H3("Requests for My Approval", className="mt-5"),
            dash_table.DataTable(
                id='approval-requests-table',
                # ... (rest of table props)
            ),
        ]
    else:
        app.logger.info(f"User {user_first_name} is not a manager. Approval section hidden.")
        # Explicitly add a hidden div for the table to ensure its ID exists for callbacks if needed
        approval_section_content = [html.Div(id='approval-requests-table', style={'display': 'none'})]


    return dbc.Container([
        dcc.Interval(
            id='dashboard-load-trigger',
            interval=100,  # milliseconds
            n_intervals=0,
            max_intervals=1 # Fire only once
        ),
        dbc.Row([
            dbc.Col(html.H2(f"Welcome, {user_first_name}!"), width=9),
            dbc.Col(dbc.Button("Logout", id="logout-button", color="secondary", className="mt-2"), width=3, className="text-end")
        ], className="mb-4 mt-4 align-items-center"),
        *my_requests_section,
        *approval_section_content # Use the variable here
    ], fluid=True)



# Main App Layout
app.layout = html.Div([
    dcc.Store(id='session-store', storage_type='session'),
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# --- Callbacks ---

# Callback to control page content based on URL and session
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname'),
     Input('session-store', 'data')]
)
def display_page(pathname, session_data):
    session_data = session_data or {}
    is_logged_in = session_data.get('logged_in', False)
    app.logger.info(f"display_page: pathname={pathname}, is_logged_in={is_logged_in}")

    if pathname == '/dashboard' and is_logged_in:
        return create_dashboard_layout(session_data)
    elif pathname == '/login' and is_logged_in:
        # If user is already logged in and tries to go to /login, redirect to dashboard
        # This requires setting url.pathname, which can't be done directly here.
        # Instead, handle_login will redirect. For now, just show dashboard.
        return create_dashboard_layout(session_data)
    elif pathname == '/dashboard' and not is_logged_in:
        # If user tries to access dashboard without login, show login page
        # (Ideally redirect to /login, handled by login callback)
        return login_layout
    else: # Covers '/' or '/login' or any other path when not logged in
        return login_layout

# Login Callback
@app.callback(
    [Output('session-store', 'data', allow_duplicate=True), # allow_duplicate for logout
     Output('login-status-message', 'children'),
     Output('url', 'pathname', allow_duplicate=True)], # allow_duplicate for logout
    [Input('login-button', 'n_clicks')],
    [State('username-input', 'value'),
     State('password-input', 'value')],
    prevent_initial_call=True
)
def handle_login(n_clicks, username, password):
    app.logger.info(f"handle_login: n_clicks={n_clicks}, username={username}")
    if not n_clicks:
        return dash.no_update, "", dash.no_update

    if not username or not password:
        return {}, dbc.Alert("Username and password are required.", color="warning"), dash.no_update

    conn = get_db_connection()
    if not conn:
        return {}, dbc.Alert("Database connection error. Please try again later.", color="danger"), dash.no_update

    session_data_to_set = {}
    login_message = ""
    redirect_path = dash.no_update

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            sql = """
                SELECT uc.employee_id, e.first_name, e.last_name, uc.password_text, e.is_manager, e.email
                FROM UserCredentials uc
                JOIN Employees e ON uc.employee_id = e.employee_id
                WHERE uc.username = %s;
            """
            cur.execute(sql, (username,))
            user_record = cur.fetchone()

            if user_record:
                if user_record['password_text'] == password: # Insecure password check!
                    session_data_to_set = {
                        'logged_in': True,
                        'employee_id': user_record['employee_id'],
                        'first_name': user_record['first_name'],
                        'last_name': user_record['last_name'],
                        'email': user_record['email'],
                        'is_manager': user_record['is_manager']
                    }
                    app.logger.info(f"Login successful for user: {username}, employee_id: {user_record['employee_id']}")
                    login_message = "" # No message needed, will redirect
                    redirect_path = '/dashboard'
                else:
                    app.logger.warning(f"Invalid password for user: {username}")
                    login_message = dbc.Alert("Invalid username or password.", color="danger")
            else:
                app.logger.warning(f"User not found: {username}")
                login_message = dbc.Alert("Invalid username or password.", color="danger")
    except psycopg2.Error as e:
        app.logger.error(f"Database query error during login: {e}")
        login_message = dbc.Alert("An error occurred during login. Please try again.", color="danger")
    finally:
        if conn:
            conn.close()
            app.logger.info("Database connection closed after login attempt.")

    return session_data_to_set, login_message, redirect_path

# Logout Callback
@app.callback(
    [Output('session-store', 'data'),
     Output('url', 'pathname')],
    [Input('logout-button', 'n_clicks')],
    prevent_initial_call=True
)
def handle_logout(n_clicks):
    app.logger.info(f"handle_logout: n_clicks={n_clicks}")
    if n_clicks:
        app.logger.info("User logged out.")
        return {}, '/login' # Clear session, redirect to login
    return dash.no_update, dash.no_update


# Helper to format date/time columns
def format_datetime_column(dt_obj):
    if isinstance(dt_obj, datetime):
        return dt_obj.strftime('%Y-%m-%d %H:%M:%S')
    return dt_obj # Return as is if None or not datetime




# Callback to populate "My Access Requests" table
@app.callback(
    [Output('my-requests-table', 'data'),
     Output('my-requests-table', 'columns')],
    [Input('dashboard-load-trigger', 'n_intervals')], # Primary trigger
    [State('session-store', 'data'),
     State('url', 'pathname')] # Use as State to check conditions
)
def update_my_requests_table(n_intervals, session_data, pathname): # n_intervals is the trigger
    # Only proceed if the interval has fired (n_intervals > 0 or however many you set for max_intervals)
    # and other conditions are met. Since max_intervals=1, n_intervals will be 1.
    if not n_intervals or n_intervals == 0:
        app.logger.info("update_my_requests_table: dashboard-load-trigger has not fired yet.")
        return [], []

    session_data = session_data or {}
    if not (session_data.get('logged_in') and pathname == '/dashboard'):
        app.logger.info(f"update_my_requests_table: Conditions not met (logged_in: {session_data.get('logged_in')}, pathname: {pathname}). Skipping update.")
        return [], []

    employee_id = session_data.get('employee_id')
    app.logger.info(f"update_my_requests_table: Triggered by interval. Fetching requests for employee_id: {employee_id} on path {pathname}")

    # ... (rest of the function for fetching and processing data remains the same)
    conn = get_db_connection()
    if not conn:
        return [], []

    data = []
    columns = [
        {"name": "Req ID", "id": "request_id"},
        {"name": "Table", "id": "table_full_name"},
        {"name": "Role", "id": "requested_role"},
        {"name": "Justification", "id": "justification"},
        {"name": "Requested", "id": "request_date_str"},
        {"name": "Status", "id": "status"},
        {"name": "Approver", "id": "approver_name"},
        {"name": "Decided", "id": "decision_date_str"},
        {"name": "Comments", "id": "approver_comments"},
    ]

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            sql = """
                SELECT
                    ar.request_id,
                    dt.schema_name || '.' || dt.table_name AS table_full_name,
                    aro.role_name AS requested_role,
                    ar.justification,
                    ar.request_date,
                    ar.status,
                    COALESCE(approver_emp.first_name || ' ' || approver_emp.last_name, 'N/A') AS approver_name,
                    ar.decision_date,
                    ar.approver_comments
                FROM AccessRequests ar
                JOIN DatabaseTables dt ON ar.table_id = dt.table_id
                JOIN AccessRoles aro ON ar.requested_role_id = aro.role_id
                LEFT JOIN Employees approver_emp ON ar.approver_id = approver_emp.employee_id
                WHERE ar.requester_id = %s
                ORDER BY ar.request_date DESC;
            """
            cur.execute(sql, (employee_id,))
            records = cur.fetchall()
            for rec in records:
                row = dict(rec)
                row['request_date_str'] = format_datetime_column(row.get('request_date'))
                row['decision_date_str'] = format_datetime_column(row.get('decision_date'))
                data.append(row)
            app.logger.info(f"update_my_requests_table: Found {len(data)} requests for employee_id: {employee_id}")
    except psycopg2.Error as e:
        app.logger.error(f"Database error in update_my_requests_table: {e}")
    finally:
        if conn:
            conn.close()
            app.logger.info("Database connection closed after update_my_requests_table.")
    return data, columns


# Callback to populate "Requests for My Approval" table
@app.callback(
    [Output('approval-requests-table', 'data'),
     Output('approval-requests-table', 'columns'),
     Output('approval-requests-table', 'style_table')],
    [Input('dashboard-load-trigger', 'n_intervals')], # Primary trigger
    [State('session-store', 'data'),
     State('url', 'pathname')] # Use as State to check conditions
)
def update_approval_requests_table(n_intervals, session_data, pathname): # n_intervals is the trigger
    if not n_intervals or n_intervals == 0:
        app.logger.info("update_approval_requests_table: dashboard-load-trigger has not fired yet.")
        return [], [], {'display': 'none'} # Important to return style too

    session_data = session_data or {}
    if not (session_data.get('logged_in') and session_data.get('is_manager') and pathname == '/dashboard'):
        app.logger.info(f"update_approval_requests_table: Conditions not met (logged_in: {session_data.get('logged_in')}, is_manager: {session_data.get('is_manager')}, pathname: {pathname}). Hiding/skipping update.")
        return [], [], {'display': 'none'}

    manager_id = session_data.get('employee_id')
    app.logger.info(f"update_approval_requests_table: Triggered by interval. Fetching pending approvals for manager_id: {manager_id} on path {pathname}")

    # ... (rest of the function for fetching and processing data remains the same)
    conn = get_db_connection()
    if not conn:
        return [], [], {'overflowX': 'auto', 'display': 'block' if session_data.get('is_manager') else 'none'}

    data = []
    columns = [
        {"name": "Req ID", "id": "request_id"},
        {"name": "Requester", "id": "requester_name"},
        {"name": "Requester Email", "id": "requester_email"},
        {"name": "Table", "id": "table_full_name"},
        {"name": "Role", "id": "requested_role"},
        {"name": "Justification", "id": "justification"},
        {"name": "Requested", "id": "request_date_str"},
    ]
    # Ensure table is visible if conditions are met, otherwise it might stay hidden from a previous non-manager login
    table_style = {'overflowX': 'auto', 'display': 'block'}

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            sql = """
                SELECT
                    ar.request_id,
                    req_emp.first_name || ' ' || req_emp.last_name AS requester_name,
                    req_emp.email AS requester_email,
                    dt.schema_name || '.' || dt.table_name AS table_full_name,
                    aro.role_name AS requested_role,
                    ar.justification,
                    ar.request_date
                FROM AccessRequests ar
                JOIN Employees req_emp ON ar.requester_id = req_emp.employee_id
                JOIN DatabaseTables dt ON ar.table_id = dt.table_id
                JOIN AccessRoles aro ON ar.requested_role_id = aro.role_id
                WHERE req_emp.manager_id = %s AND ar.status = 'Pending'
                ORDER BY ar.request_date ASC;
            """
            cur.execute(sql, (manager_id,))
            records = cur.fetchall()
            for rec in records:
                row = dict(rec)
                row['request_date_str'] = format_datetime_column(row.get('request_date'))
                data.append(row)
            app.logger.info(f"update_approval_requests_table: Found {len(data)} pending approvals for manager_id: {manager_id}")

    except psycopg2.Error as e:
        app.logger.error(f"Database error in update_approval_requests_table: {e}")
    finally:
        if conn:
            conn.close()
            app.logger.info("Database connection closed after update_approval_requests_table.")

    return data, columns, table_style



# --- Main execution ---
if __name__ == '__main__':
    app.logger.info("Starting Dash application...")
    app.logger.info("Access it at http://127.0.0.1:8050/")
    app.logger.warning("--- SECURITY NOTE ---")
    app.logger.warning("This application uses PLAINTEXT password checking as per the provided database schema.")
    app.logger.warning("This is INSECURE and NOT SUITABLE for production environments.")
    app.logger.warning("In a real-world scenario, passwords MUST be securely HASHED and SALTED.")
    app.logger.warning("---")
    app.run(debug=True, port=8050)