# app.py

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ctx, dash_table, ALL, no_update
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
app.title = "Internal DB Access System"

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

# Login Layout
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
                        html.Div(id="login-status-message", className="mt-3 text-center")
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

    my_requests_section_ui = [
        html.H3("My Access Requests", className="mt-4"),
        dash_table.DataTable(
            id='my-requests-table',
            style_cell={'textAlign': 'left', 'minWidth': '100px', 'width': '150px', 'maxWidth': '300px', 'whiteSpace': 'normal', 'height': 'auto'},
            style_header={'fontWeight': 'bold'},
            style_table={'overflowX': 'auto'},
            page_size=10,
            row_selectable='single', # Make rows selectable
            selected_rows=[],
        ),
        html.Div(id='my-request-action-panel', className="mt-3 p-3 border rounded", style={'display': 'none'}) # Panel for actions
    ]

    approval_section_content = []
    if is_manager:
        app.logger.info(f"User {user_first_name} is a manager. Adding approval section.")
        approval_section_content = [
            html.H3("Requests Requiring My Action / History", className="mt-5"), # Renamed for clarity
            dash_table.DataTable(
                id='approval-requests-table',
                style_cell={'textAlign': 'left', 'minWidth': '100px', 'width': '150px', 'maxWidth': '300px', 'whiteSpace': 'normal', 'height': 'auto'},
                style_header={'fontWeight': 'bold'},
                style_table={'overflowX': 'auto'},
                page_size=5,
                row_selectable='single', # Make rows selectable
                selected_rows=[],
            ),
            html.Div(id='approval-action-panel', className="mt-3 p-3 border rounded", style={'display': 'none'}) # Panel for approval actions
        ]
    else:
        app.logger.info(f"User {user_first_name} is not a manager. Approval section hidden.")
        approval_section_content = [
            html.Div(id='approval-requests-table', style={'display': 'none'}),
            html.Div(id='approval-action-panel', style={'display': 'none'})
            ]


    return dbc.Container([
        dcc.Interval(
            id='dashboard-load-trigger',
            interval=100,
            n_intervals=0,
            max_intervals=1
        ),
        dcc.Store(id='selected-request-id-store'), 
        dcc.Store(id='selected-approval-request-id-store'),
        dbc.Row([
            dbc.Col(html.H2(f"Welcome, {user_first_name}!"), width=9),
            dbc.Col(dbc.Button("Logout", id="logout-button", color="secondary", className="mt-2"), width=3, className="text-end")
        ], className="mb-4 mt-4 align-items-center"),
        html.Div(id='action-feedback-alert-placeholder'),
        *my_requests_section_ui,
        *approval_section_content
    ], fluid=True)


# Main App Layout
app.layout = html.Div([
    dcc.Store(id='session-store', storage_type='session'),
    dcc.Store(id='refresh-trigger-store', data=0),
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# --- Callbacks ---

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
    else:
        return login_layout

@app.callback(
    [Output('session-store', 'data', allow_duplicate=True),
     Output('login-status-message', 'children'),
     Output('url', 'pathname', allow_duplicate=True)],
    [Input('login-button', 'n_clicks')],
    [State('username-input', 'value'),
     State('password-input', 'value')],
    prevent_initial_call=True
)
def handle_login(n_clicks, username, password):
    app.logger.info(f"handle_login: n_clicks={n_clicks}, username={username}")
    if not n_clicks: return dash.no_update, "", dash.no_update
    if not username or not password: return {}, dbc.Alert("Username and password are required.", color="warning"), dash.no_update
    conn = get_db_connection()
    if not conn: return {}, dbc.Alert("Database connection error. Please try again later.", color="danger"), dash.no_update
    session_data_to_set, login_message, redirect_path = {}, "", dash.no_update
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT uc.employee_id, e.first_name, e.last_name, uc.password_text, e.is_manager, e.email FROM UserCredentials uc JOIN Employees e ON uc.employee_id = e.employee_id WHERE uc.username = %s;", (username,))
            user_record = cur.fetchone()
            if user_record:
                if user_record['password_text'] == password:
                    session_data_to_set = {'logged_in': True, 'employee_id': user_record['employee_id'], 'first_name': user_record['first_name'], 'last_name': user_record['last_name'], 'email': user_record['email'], 'is_manager': user_record['is_manager']}
                    app.logger.info(f"Login successful for user: {username}, employee_id: {user_record['employee_id']}")
                    redirect_path = '/dashboard'
                else:
                    app.logger.warning(f"Invalid password for user: {username}"); login_message = dbc.Alert("Invalid username or password.", color="danger")
            else:
                app.logger.warning(f"User not found: {username}"); login_message = dbc.Alert("Invalid username or password.", color="danger")
    except psycopg2.Error as e:
        app.logger.error(f"Database query error during login: {e}"); login_message = dbc.Alert("An error occurred during login. Please try again.", color="danger")
    finally:
        if conn: conn.close(); app.logger.info("Database connection closed after login attempt.")
    return session_data_to_set, login_message, redirect_path

@app.callback(
    [Output('session-store', 'data'), Output('url', 'pathname')],
    [Input('logout-button', 'n_clicks')],
    prevent_initial_call=True
)
def handle_logout(n_clicks):
    app.logger.info(f"handle_logout: n_clicks={n_clicks}")
    if n_clicks: app.logger.info("User logged out."); return {}, '/login'
    return dash.no_update, dash.no_update

def format_datetime_column(dt_obj):
    return dt_obj.strftime('%Y-%m-%d %H:%M:%S') if isinstance(dt_obj, datetime) else dt_obj

@app.callback(
    [Output('my-requests-table', 'data'), Output('my-requests-table', 'columns'), Output('my-requests-table', 'selected_rows', allow_duplicate=True)],
    [Input('dashboard-load-trigger', 'n_intervals'), Input('refresh-trigger-store', 'data')],
    [State('session-store', 'data'), State('url', 'pathname')],
    prevent_initial_call=True
)
def update_my_requests_table(n_intervals_load, refresh_trigger, session_data, pathname):
    app.logger.info(f"update_my_requests_table triggered by: {ctx.triggered_id}")
    session_data = session_data or {}
    if not (session_data.get('logged_in') and pathname == '/dashboard'): app.logger.info(f"update_my_requests_table: Conditions not met."); return [], [], []
    employee_id = session_data.get('employee_id')
    app.logger.info(f"update_my_requests_table: Fetching requests for employee_id: {employee_id}")
    conn = get_db_connection()
    if not conn: return [], [], []
    data, columns = [], [{"name": c, "id": i} for c, i in [("Req ID", "request_id"), ("Table", "table_full_name"), ("Role", "requested_role"), ("Justification", "justification"), ("Requested", "request_date_str"), ("Status", "status"), ("Approver", "approver_name"), ("Decided", "decision_date_str"), ("Comments", "approver_comments")]]
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT ar.request_id, ar.requester_id, dt.schema_name || '.' || dt.table_name AS table_full_name, aro.role_name AS requested_role, ar.justification, ar.request_date, ar.status, COALESCE(approver_emp.first_name || ' ' || approver_emp.last_name, 'N/A') AS approver_name, ar.decision_date, ar.approver_comments FROM AccessRequests ar JOIN DatabaseTables dt ON ar.table_id = dt.table_id JOIN AccessRoles aro ON ar.requested_role_id = aro.role_id LEFT JOIN Employees approver_emp ON ar.approver_id = approver_emp.employee_id WHERE ar.requester_id = %s ORDER BY ar.request_date DESC;", (employee_id,))
            for rec in cur.fetchall(): row = dict(rec); row['request_date_str'] = format_datetime_column(row.get('request_date')); row['decision_date_str'] = format_datetime_column(row.get('decision_date')); data.append(row)
            app.logger.info(f"update_my_requests_table: Found {len(data)} requests for employee_id: {employee_id}")
    except Exception as e: app.logger.error(f"Error in update_my_requests_table: {e}")
    finally:
        if conn: conn.close(); app.logger.info("DB connection closed after update_my_requests_table.")
    return data, columns, []

@app.callback(
    [Output('approval-requests-table', 'data'), Output('approval-requests-table', 'columns'), Output('approval-requests-table', 'style_table'), Output('approval-requests-table', 'selected_rows', allow_duplicate=True)],
    [Input('dashboard-load-trigger', 'n_intervals'), Input('refresh-trigger-store', 'data')],
    [State('session-store', 'data'), State('url', 'pathname')],
    prevent_initial_call=True
)
def update_approval_requests_table(n_intervals_load, refresh_trigger, session_data, pathname):
    app.logger.info(f"update_approval_requests_table triggered by: {ctx.triggered_id}")
    session_data = session_data or {}
    if not (session_data.get('logged_in') and session_data.get('is_manager') and pathname == '/dashboard'): app.logger.info(f"update_approval_requests_table: Conditions not met."); return [], [], {'display': 'none'}, []
    manager_id = session_data.get('employee_id')
    app.logger.info(f"update_approval_requests_table: Fetching requests for manager_id: {manager_id}")
    conn = get_db_connection()
    if not conn: return [], [], {'overflowX': 'auto', 'display': 'block'}, []
    data, columns, table_style = [], [{"name": c, "id": i} for c, i in [("Req ID", "request_id"), ("Requester", "requester_name"), ("Requester Email", "requester_email"), ("Table", "table_full_name"), ("Role", "requested_role"), ("Justification", "justification"), ("Requested", "request_date_str"), ("Status", "status")]], {'overflowX': 'auto', 'display': 'block'} # Added Status to columns
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Modified SQL to show all history, not just pending
            cur.execute("SELECT ar.request_id, req_emp.first_name || ' ' || req_emp.last_name AS requester_name, req_emp.email AS requester_email, dt.schema_name || '.' || dt.table_name AS table_full_name, aro.role_name AS requested_role, ar.justification, ar.request_date, ar.status FROM AccessRequests ar JOIN Employees req_emp ON ar.requester_id = req_emp.employee_id JOIN DatabaseTables dt ON ar.table_id = dt.table_id JOIN AccessRoles aro ON ar.requested_role_id = aro.role_id WHERE req_emp.manager_id = %s ORDER BY ar.request_date DESC;", (manager_id,))
            for rec in cur.fetchall(): row = dict(rec); row['request_date_str'] = format_datetime_column(row.get('request_date')); data.append(row)
            app.logger.info(f"update_approval_requests_table: Found {len(data)} requests for manager_id: {manager_id}")
    except Exception as e: app.logger.error(f"Error in update_approval_requests_table: {e}")
    finally:
        if conn: conn.close(); app.logger.info("DB conn closed after update_approval_requests_table.")
    return data, columns, table_style, []

@app.callback(
    [Output('my-request-action-panel', 'children'), Output('my-request-action-panel', 'style'), Output('selected-request-id-store', 'data')],
    [Input('my-requests-table', 'selected_rows')],
    [State('my-requests-table', 'data'), State('session-store', 'data')]
)
def update_my_request_action_panel(selected_rows, table_data, session_data):
    if not selected_rows or not table_data: app.logger.info("My Request Action Panel: No row selected or no data."); return [], {'display': 'none'}, None
    selected_request = table_data[selected_rows[0]]
    request_id, request_status, requester_id_from_table, current_user_id = selected_request['request_id'], selected_request['status'], selected_request['requester_id'], session_data.get('employee_id')
    app.logger.info(f"My Request Action Panel: Selected request_id {request_id}, status {request_status}, requester {requester_id_from_table}, current_user {current_user_id}")
    if request_status == 'Pending' and requester_id_from_table == current_user_id:
        panel_content = [html.H5(f"Action for Request ID: {request_id}"), html.P(f"Table: {selected_request['table_full_name']}, Role: {selected_request['requested_role']}"), dbc.Button("Cancel My Request", id="cancel-my-request-button", color="warning", className="mt-2")]
        return panel_content, {'display': 'block', 'marginTop': '15px', 'padding': '15px', 'border': '1px solid #ddd', 'borderRadius': '5px'}, request_id
    app.logger.info(f"My Request Action Panel: Request {request_id} not actionable by user."); return [], {'display': 'none'}, None

@app.callback(
    [Output('approval-action-panel', 'children'), Output('approval-action-panel', 'style'), Output('selected-approval-request-id-store', 'data')],
    [Input('approval-requests-table', 'selected_rows')],
    [State('approval-requests-table', 'data')]
)
def update_approval_action_panel(selected_rows, table_data):
    if not selected_rows or not table_data: app.logger.info("Approval Action Panel: No row selected or no data."); return [], {'display': 'none'}, None
    selected_request = table_data[selected_rows[0]]
    request_id, request_status = selected_request['request_id'], selected_request.get('status', 'Pending')
    app.logger.info(f"Approval Action Panel: Selected request_id {request_id}, status {request_status}")
    if request_status == 'Pending':
        panel_content = [
            html.H5(f"Action for Request ID: {request_id}"), html.P(f"Requester: {selected_request['requester_name']} ({selected_request['requester_email']})"),
            html.P(f"Table: {selected_request['table_full_name']}, Role: {selected_request['requested_role']}"), html.P(f"Justification: {selected_request['justification']}"),
            dbc.Textarea(id="approver-comment-input", placeholder="Comments (required for Reject)", className="mb-2"),
            dbc.Button("Approve", id="approve-request-button", color="success", className="me-2"), dbc.Button("Reject", id="reject-request-button", color="danger")
        ]
        return panel_content, {'display': 'block', 'marginTop': '15px', 'padding': '15px', 'border': '1px solid #ddd', 'borderRadius': '5px'}, request_id
    else: # If already actioned, show details without action buttons
        panel_content = [
            html.H5(f"Details for Request ID: {request_id} (Status: {request_status})"),
            html.P(f"Requester: {selected_request['requester_name']} ({selected_request['requester_email']})"),
            html.P(f"Table: {selected_request['table_full_name']}, Role: {selected_request['requested_role']}")
        ]
        return panel_content, {'display': 'block', 'marginTop': '15px', 'padding': '15px', 'border': '1px solid #ddd', 'borderRadius': '5px'}, request_id
    app.logger.info(f"Approval Action Panel: Request {request_id} not pending."); return [], {'display': 'none'}, None

@app.callback(
    [Output('refresh-trigger-store', 'data', allow_duplicate=True), Output('action-feedback-alert-placeholder', 'children', allow_duplicate=True), Output('my-request-action-panel', 'style', allow_duplicate=True), Output('my-requests-table', 'selected_rows', allow_duplicate=True)],
    [Input('cancel-my-request-button', 'n_clicks')],
    [State('selected-request-id-store', 'data'), State('session-store', 'data'), State('refresh-trigger-store', 'data')],
    prevent_initial_call=True
)
def handle_cancel_my_request(n_clicks, request_id, session_data, current_refresh_count):
    if not n_clicks or not request_id: app.logger.info("handle_cancel_my_request: No click or no request_id."); return no_update, no_update, no_update, no_update
    employee_id = session_data.get('employee_id')
    app.logger.info(f"handle_cancel_my_request: Attempting to cancel request_id {request_id} by employee_id {employee_id}")
    conn = get_db_connection()
    if not conn: return no_update, dbc.Alert("Database connection error.", color="danger", dismissable=True, duration=4000), no_update, no_update
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE AccessRequests SET status = 'Rejected', approver_id = %s, decision_date = CURRENT_TIMESTAMP, approver_comments = 'Cancelled by requester.' WHERE request_id = %s AND requester_id = %s AND status = 'Pending';", (employee_id, request_id, employee_id))
            conn.commit()
            if cur.rowcount > 0:
                app.logger.info(f"Request {request_id} cancelled successfully by employee {employee_id}.")
                return current_refresh_count + 1, dbc.Alert(f"Request ID {request_id} cancelled.", color="success", dismissable=True, duration=4000), {'display': 'none'}, []
            app.logger.warning(f"Failed to cancel request {request_id}."); return no_update, dbc.Alert(f"Failed to cancel request ID {request_id}.", color="warning", dismissable=True, duration=4000), no_update, no_update
    except psycopg2.Error as e:
        conn.rollback(); app.logger.error(f"DB error cancelling request {request_id}: {e}")
        return no_update, dbc.Alert(f"Error cancelling request {request_id}.", color="danger", dismissable=True, duration=4000), no_update, no_update
    finally:
        if conn: conn.close()
    return no_update, no_update, no_update, no_update


@app.callback(
    [Output('refresh-trigger-store', 'data', allow_duplicate=True), Output('action-feedback-alert-placeholder', 'children', allow_duplicate=True), Output('approval-action-panel', 'style', allow_duplicate=True), Output('approval-requests-table', 'selected_rows', allow_duplicate=True)],
    [Input('approve-request-button', 'n_clicks'), Input('reject-request-button', 'n_clicks')],
    [State('selected-approval-request-id-store', 'data'), State('approver-comment-input', 'value'), State('session-store', 'data'), State('refresh-trigger-store', 'data')],
    prevent_initial_call=True
)
def handle_approval_decision(approve_clicks, reject_clicks, request_id, comment_text, session_data, current_refresh_count):
    triggered_prop_ids = ctx.triggered_prop_ids
    app.logger.info(f"handle_approval_decision triggered_prop_ids: {triggered_prop_ids}, approve_clicks: {approve_clicks}, reject_clicks: {reject_clicks}, request_id: {request_id}")

    # Determine which button was clicked based on which n_clicks is not None and part of triggered_props
    # And ensure the n_click count is positive (i.e., it's an actual click event)
    action_button_id = None
    if triggered_prop_ids.get("approve-request-button.n_clicks") and approve_clicks and approve_clicks > 0:
        action_button_id = "approve-request-button"
    elif triggered_prop_ids.get("reject-request-button.n_clicks") and reject_clicks and reject_clicks > 0:
        action_button_id = "reject-request-button"
    
    if not action_button_id:
        app.logger.info("handle_approval_decision: No valid button click with positive n_clicks detected or initial callback noise.")
        return no_update, no_update, no_update, no_update
    
    if not request_id: 
        app.logger.info("handle_approval_decision: request_id from store is missing.")
        return no_update, no_update, no_update, no_update

    approver_employee_id = session_data.get('employee_id')
    action_type, new_status, final_comment = "", "", ""

    if action_button_id == 'approve-request-button':
        action_type, new_status = "approve", "Approved"
        final_comment = comment_text if comment_text else "Approved by manager."
    elif action_button_id == 'reject-request-button':
        action_type, new_status = "reject", "Rejected"
        if not comment_text:
            app.logger.warning(f"Reject action for request {request_id} by {approver_employee_id} without comments.")
            return no_update, dbc.Alert("Comments are required for rejection.", color="warning", dismissable=True, duration=4000), no_update, no_update
        final_comment = comment_text
    
    app.logger.info(f"handle_approval_decision: Action '{action_type}' on request_id {request_id} by approver_id {approver_employee_id} with comment '{final_comment}'")
    conn = get_db_connection()
    if not conn: return no_update, dbc.Alert("Database connection error.", color="danger", dismissable=True, duration=4000), no_update, no_update
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE AccessRequests SET status = %s, approver_id = %s, decision_date = CURRENT_TIMESTAMP, approver_comments = %s WHERE request_id = %s AND status = 'Pending' AND EXISTS (SELECT 1 FROM Employees req_emp WHERE req_emp.employee_id = AccessRequests.requester_id AND req_emp.manager_id = %s);", (new_status, approver_employee_id, final_comment, request_id, approver_employee_id))
            conn.commit()
            if cur.rowcount > 0:
                app.logger.info(f"Request {request_id} {new_status.lower()} successfully by manager {approver_employee_id}.")
                return current_refresh_count + 1, dbc.Alert(f"Request ID {request_id} has been {new_status.lower()}.", color="success", dismissable=True, duration=4000), {'display': 'none'}, []
            app.logger.warning(f"Failed to {action_type} request {request_id}. Not pending or not authorized."); return no_update, dbc.Alert(f"Failed to {action_type} request ID {request_id}.", color="warning", dismissable=True, duration=4000), no_update, no_update
    except psycopg2.Error as e:
        conn.rollback(); app.logger.error(f"DB error {action_type}ing request {request_id}: {e}")
        return no_update, dbc.Alert(f"Error {action_type}ing request {request_id}.", color="danger", dismissable=True, duration=4000), no_update, no_update
    finally:
        if conn: conn.close()
    return no_update, no_update, no_update, no_update

# --- Main execution ---
if __name__ == '__main__':
    app.logger.info("Starting Dash application...")
    app.run(debug=True, port=8050)