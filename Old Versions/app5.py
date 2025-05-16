# app.py

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ctx, dash_table, ALL, no_update
import psycopg2
import psycopg2.extras # For dictionary cursor
import logging
from datetime import datetime # For formatting dates
import pandas as pd # For CSV generation

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

    new_request_button_ui = [
        dbc.Button("New Access Request", id="open-new-request-modal-button", color="primary", className="mb-3 mt-3")
    ]

    new_request_modal = dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Submit New Access Request")),
            dbc.ModalBody([
                dbc.Form([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Target Database Table", html_for="new-request-table-dropdown"),
                            dcc.Dropdown(id="new-request-table-dropdown", placeholder="Select Table..."),
                        ], width=12)
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Required Access Level", html_for="new-request-role-dropdown"),
                            dcc.Dropdown(id="new-request-role-dropdown", placeholder="Select Role..."),
                        ], width=12)
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Justification", html_for="new-request-justification-textarea"),
                            dbc.Textarea(id="new-request-justification-textarea", placeholder="Explain why you need this access (min 20 characters)", style={'minHeight': '100px'}),
                        ], width=12)
                    ], className="mb-3"),
                    html.Div(id="new-request-form-feedback", className="mt-2") # For modal-specific feedback
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("Submit Request", id="submit-new-request-button", color="success"),
                dbc.Button("Cancel", id="cancel-new-request-modal-button", color="secondary", className="ms-1"),
            ]),
        ],
        id="new-request-modal",
        is_open=False,
        size="lg",
    )

    my_requests_section_ui = [
        html.H3("My Access Requests", className="mt-4"),
        dash_table.DataTable(
            id='my-requests-table',
            style_cell={'textAlign': 'left', 'minWidth': '100px', 'width': '150px', 'maxWidth': '300px', 'whiteSpace': 'normal', 'height': 'auto'},
            style_header={'fontWeight': 'bold'},
            style_table={'overflowX': 'auto'},
            page_size=10,
            row_selectable='single',
            selected_rows=[],
        ),
        html.Div(id='my-request-action-panel', className="mt-3 p-3 border rounded", style={'display': 'none'})
    ]

    approval_section_content = []
    if is_manager:
        app.logger.info(f"User {user_first_name} is a manager. Adding approval section.")
        approval_section_content = [
            html.H3("Requests Requiring My Action / History", className="mt-5"),
            dash_table.DataTable(
                id='approval-requests-table',
                style_cell={'textAlign': 'left', 'minWidth': '100px', 'width': '150px', 'maxWidth': '300px', 'whiteSpace': 'normal', 'height': 'auto'},
                style_header={'fontWeight': 'bold'},
                style_table={'overflowX': 'auto'},
                page_size=5,
                row_selectable='single',
                selected_rows=[],
            ),
            html.Div(id='approval-action-panel', className="mt-3 p-3 border rounded", style={'display': 'none'})
        ]
    else:
        app.logger.info(f"User {user_first_name} is not a manager. Approval section hidden.")
        approval_section_content = [
            html.Div(id='approval-requests-table', style={'display': 'none'}),
            html.Div(id='approval-action-panel', style={'display': 'none'})
            ]

    reports_section_ui = [
        html.H3("Generate Reports", className="mt-5"),
        dbc.Row([
            dbc.Col([
                dcc.Dropdown(
                    id='report-type-dropdown',
                    options=[
                        {'label': 'Access Request Audit Log', 'value': 'audit_log'},
                        {'label': 'User Access Permissions Report', 'value': 'user_permissions'},
                        {'label': 'Pending Access Requests Report', 'value': 'pending_requests'},
                    ],
                    placeholder="Select a report type...",
                    className="mb-2"
                ),
            ], width=6),
            dbc.Col([
                dbc.Button("Download Report (CSV)", id="download-report-button", color="info", className="w-100"),
            ], width=3),
        ], className="mb-3 align-items-center"),
        dcc.Download(id="download-csv"), # Component to trigger file download
        html.Div(id="report-generation-feedback", className="mt-2") # For report specific feedback
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
        html.Div(id='action-feedback-alert-placeholder'), # For global alerts
        *new_request_button_ui,
        new_request_modal,
        *my_requests_section_ui,
        *approval_section_content,
        *reports_section_ui # Added reports section
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
    data, columns, table_style = [], [{"name": c, "id": i} for c, i in [("Req ID", "request_id"), ("Requester", "requester_name"), ("Requester Email", "requester_email"), ("Table", "table_full_name"), ("Role", "requested_role"), ("Justification", "justification"), ("Requested", "request_date_str"), ("Status", "status")]], {'overflowX': 'auto', 'display': 'block'}
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
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
    else:
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
        if conn: conn.close(); app.logger.info("DB conn closed after handle_cancel_my_request.")
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
        if conn: conn.close(); app.logger.info("DB conn closed after handle_approval_decision.")
    return no_update, no_update, no_update, no_update


# --- Callbacks for New Request Modal ---
@app.callback(
    [Output('new-request-modal', 'is_open', allow_duplicate=True),
     Output('new-request-table-dropdown', 'options'),
     Output('new-request-role-dropdown', 'options'),
     Output('new-request-table-dropdown', 'value', allow_duplicate=True),
     Output('new-request-role-dropdown', 'value', allow_duplicate=True),
     Output('new-request-justification-textarea', 'value', allow_duplicate=True),
     Output('new-request-form-feedback', 'children', allow_duplicate=True)],
    [Input('open-new-request-modal-button', 'n_clicks'),
     Input('cancel-new-request-modal-button', 'n_clicks')],
    [State('new-request-modal', 'is_open'),
     State('session-store', 'data')],
    prevent_initial_call=True
)
def toggle_and_populate_new_request_modal(n_open, n_cancel, is_open_state, session_data):
    triggered_id = ctx.triggered_id
    app.logger.info(f"toggle_and_populate_new_request_modal: triggered_id={triggered_id}, n_open={n_open}, n_cancel={n_cancel}, current_is_open={is_open_state}")

    table_options, role_options = [], []
    reset_table_val, reset_role_val, reset_just_val = None, None, ""
    modal_specific_feedback = ""

    if triggered_id == 'open-new-request-modal-button' and n_open:
        app.logger.info("toggle_and_populate_new_request_modal: Opening modal and populating dropdowns.")
        conn = get_db_connection()
        if conn and session_data and session_data.get('logged_in'):
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("SELECT table_id, schema_name || '.' || table_name AS full_name FROM DatabaseTables ORDER BY full_name;")
                    table_options = [{'label': r['full_name'], 'value': r['table_id']} for r in cur.fetchall()]
                    app.logger.info(f"Fetched {len(table_options)} tables for dropdown.")

                    cur.execute("SELECT role_id, role_name FROM AccessRoles ORDER BY role_name;")
                    role_options = [{'label': r['role_name'], 'value': r['role_id']} for r in cur.fetchall()]
                    app.logger.info(f"Fetched {len(role_options)} roles for dropdown.")
            except psycopg2.Error as e:
                app.logger.error(f"DB error fetching data for new request modal: {e}")
                modal_specific_feedback = dbc.Alert("Error loading form data. Please try again.", color="danger")
            finally:
                if conn: conn.close(); app.logger.info("DB conn closed after populating new request modal.")
            return True, table_options, role_options, reset_table_val, reset_role_val, reset_just_val, modal_specific_feedback
        else:
            app.logger.warning("toggle_and_populate_new_request_modal: No DB connection or not logged in for opening modal.")
            modal_specific_feedback = dbc.Alert("Cannot open form. Please ensure you are logged in and the system is available.", color="warning")
            return False, [], [], reset_table_val, reset_role_val, reset_just_val, modal_specific_feedback

    if triggered_id == 'cancel-new-request-modal-button' and n_cancel:
        app.logger.info("toggle_and_populate_new_request_modal: Closing modal due to cancel button.")
        return False, dash.no_update, dash.no_update, reset_table_val, reset_role_val, reset_just_val, ""

    app.logger.info("toggle_and_populate_new_request_modal: No direct open/cancel trigger, maintaining modal state or default.")
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

@app.callback(
    [Output('new-request-form-feedback', 'children', allow_duplicate=True),
     Output('refresh-trigger-store', 'data', allow_duplicate=True),
     Output('new-request-modal', 'is_open', allow_duplicate=True),
     Output('new-request-table-dropdown', 'value', allow_duplicate=True),
     Output('new-request-role-dropdown', 'value', allow_duplicate=True),
     Output('new-request-justification-textarea', 'value', allow_duplicate=True),
     Output('action-feedback-alert-placeholder', 'children', allow_duplicate=True)],
    [Input('submit-new-request-button', 'n_clicks')],
    [State('new-request-table-dropdown', 'value'),
     State('new-request-role-dropdown', 'value'),
     State('new-request-justification-textarea', 'value'),
     State('session-store', 'data'),
     State('refresh-trigger-store', 'data')],
    prevent_initial_call=True
)
def submit_new_request(n_clicks_submit, table_id, role_id, justification, session_data, current_refresh_count):
    app.logger.info(f"submit_new_request: n_clicks={n_clicks_submit}, table_id={table_id}, role_id={role_id}, justification_len={len(justification or '')}")

    if not n_clicks_submit:
        app.logger.info("submit_new_request: No submit click, no action.")
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update

    modal_feedback, new_refresh_count, modal_is_open = no_update, no_update, True
    global_feedback = no_update
    reset_table, reset_role, reset_justification = no_update, no_update, no_update

    if not all([table_id, role_id, justification]):
        app.logger.warning("submit_new_request: Validation failed - missing fields.")
        modal_feedback = dbc.Alert("All fields are required. Please fill out the entire form.", color="warning", dismissable=True)
        return modal_feedback, new_refresh_count, modal_is_open, reset_table, reset_role, reset_justification, global_feedback

    if len(justification) < 20:
        app.logger.warning("submit_new_request: Validation failed - justification too short.")
        modal_feedback = dbc.Alert("Justification must be at least 20 characters long.", color="warning", dismissable=True)
        return modal_feedback, new_refresh_count, modal_is_open, reset_table, reset_role, reset_justification, global_feedback

    if not session_data or not session_data.get('logged_in'):
        app.logger.error("submit_new_request: User not logged in.")
        modal_feedback = dbc.Alert("Authentication error. Please log in again.", color="danger", dismissable=True)
        modal_is_open = False
        return modal_feedback, new_refresh_count, modal_is_open, reset_table, reset_role, reset_justification, global_feedback

    requester_id = session_data.get('employee_id')
    app.logger.info(f"submit_new_request: Attempting to submit request for requester_id={requester_id}, table={table_id}, role={role_id}")

    conn = get_db_connection()
    if not conn:
        modal_feedback = dbc.Alert("Database connection error. Please try again later.", color="danger", dismissable=True)
        return modal_feedback, new_refresh_count, modal_is_open, reset_table, reset_role, reset_justification, global_feedback

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO AccessRequests (requester_id, table_id, requested_role_id, justification, request_date, status)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, 'Pending')
                RETURNING request_id;
                """,
                (requester_id, table_id, role_id, justification)
            )
            new_request_id = cur.fetchone()[0]
            conn.commit()
            app.logger.info(f"New access request submitted successfully. Request ID: {new_request_id} by requester {requester_id}")
            global_feedback = dbc.Alert(f"Access request (ID: {new_request_id}) submitted successfully!", color="success", duration=5000, dismissable=True)
            new_refresh_count = current_refresh_count + 1
            modal_is_open = False
            modal_feedback = ""
            reset_table, reset_role, reset_justification = None, None, ""
    except psycopg2.Error as e:
        conn.rollback()
        app.logger.error(f"Database error submitting new request: {e}")
        modal_feedback = dbc.Alert(f"Error submitting request: {e}", color="danger", dismissable=True)
    except Exception as e:
        app.logger.error(f"Unexpected error submitting new request: {e}")
        modal_feedback = dbc.Alert("An unexpected error occurred. Please try again.", color="danger", dismissable=True)
    finally:
        if conn: conn.close(); app.logger.info("DB conn closed after submit_new_request.")

    return modal_feedback, new_refresh_count, modal_is_open, reset_table, reset_role, reset_justification, global_feedback


# --- Callback for Report Generation ---
@app.callback(
    [Output('download-csv', 'data'),
     Output('report-generation-feedback', 'children')],
    [Input('download-report-button', 'n_clicks')],
    [State('report-type-dropdown', 'value'),
     State('session-store', 'data')],
    prevent_initial_call=True
)
def generate_report_download(n_clicks, report_type, session_data):
    app.logger.info(f"generate_report_download: n_clicks={n_clicks}, report_type={report_type}")
    if not n_clicks:
        return no_update, no_update

    if not report_type:
        app.logger.warning("generate_report_download: No report type selected.")
        return no_update, dbc.Alert("Please select a report type.", color="warning", dismissable=True, duration=4000)

    user_email = session_data.get('email', 'UnknownUser')
    app.logger.info(f"User '{user_email}' initiated report generation for type: {report_type}")

    conn = get_db_connection()
    if not conn:
        app.logger.error("generate_report_download: Database connection failed.")
        return no_update, dbc.Alert("Database connection error. Cannot generate report.", color="danger", dismissable=True, duration=4000)

    query = ""
    filename_prefix = ""
    df = None

    try:
        if report_type == 'audit_log':
            filename_prefix = "access_request_audit_log"
            query = """
                SELECT
                    ar.request_id AS "Request ID",
                    req_emp.first_name || ' ' || req_emp.last_name AS "Requester Name",
                    req_emp.department AS "Requester Department",
                    dt.schema_name || '.' || dt.table_name AS "Target Table",
                    aro.role_name AS "Requested Role",
                    ar.justification AS "Justification",
                    ar.request_date AS "Request Date",
                    ar.status AS "Status",
                    COALESCE(app_emp.first_name || ' ' || app_emp.last_name, 'N/A') AS "Approver Name",
                    ar.decision_date AS "Decision Date",
                    ar.approver_comments AS "Approver Comments"
                FROM AccessRequests ar
                JOIN Employees req_emp ON ar.requester_id = req_emp.employee_id
                JOIN DatabaseTables dt ON ar.table_id = dt.table_id
                JOIN AccessRoles aro ON ar.requested_role_id = aro.role_id
                LEFT JOIN Employees app_emp ON ar.approver_id = app_emp.employee_id
                ORDER BY ar.request_id DESC;
            """
        elif report_type == 'user_permissions':
            filename_prefix = "user_access_permissions_report"
            query = """
                SELECT
                    e.first_name || ' ' || e.last_name AS "Employee Name",
                    e.email AS "Employee Email",
                    e.department AS "Employee Department",
                    dt.schema_name || '.' || dt.table_name AS "Target Table",
                    aro.role_name AS "Approved Role",
                    ar.decision_date AS "Approval Date",
                    COALESCE(app_mgr.first_name || ' ' || app_mgr.last_name, 'N/A') AS "Approved By Manager Name"
                FROM AccessRequests ar
                JOIN Employees e ON ar.requester_id = e.employee_id
                JOIN DatabaseTables dt ON ar.table_id = dt.table_id
                JOIN AccessRoles aro ON ar.requested_role_id = aro.role_id
                LEFT JOIN Employees app_mgr ON ar.approver_id = app_mgr.employee_id
                WHERE ar.status = 'Approved'
                ORDER BY "Employee Name", "Target Table";
            """
        elif report_type == 'pending_requests':
            filename_prefix = "pending_access_requests_report"
            query = """
                SELECT
                    ar.request_id AS "Request ID",
                    req_emp.first_name || ' ' || req_emp.last_name AS "Requester Name",
                    dt.schema_name || '.' || dt.table_name AS "Target Table",
                    aro.role_name AS "Requested Role",
                    ar.request_date AS "Request Date",
                    ROUND(EXTRACT(EPOCH FROM (NOW() - ar.request_date)) / (60*60*24), 2) AS "Days Pending",
                    COALESCE(mgr_emp.first_name || ' ' || mgr_emp.last_name, 'N/A (No Manager)') AS "Assigned Manager Name"
                FROM AccessRequests ar
                JOIN Employees req_emp ON ar.requester_id = req_emp.employee_id
                JOIN DatabaseTables dt ON ar.table_id = dt.table_id
                JOIN AccessRoles aro ON ar.requested_role_id = aro.role_id
                LEFT JOIN Employees mgr_emp ON req_emp.manager_id = mgr_emp.employee_id
                WHERE ar.status = 'Pending'
                ORDER BY ar.request_date ASC;
            """
        else:
            app.logger.warning(f"generate_report_download: Unknown report type '{report_type}'.")
            return no_update, dbc.Alert(f"Unknown report type: {report_type}", color="danger", dismissable=True, duration=4000)

        app.logger.info(f"Executing query for report: {report_type}")
        df = pd.read_sql_query(query, conn)
        app.logger.info(f"Fetched {len(df)} rows for report: {report_type}")

        # Format datetime columns if they exist (pandas might convert them)
        for col in df.columns:
            if 'date' in col.lower() or 'timestamp' in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e_format: # Handle cases where conversion might fail or column is not datetime
                    app.logger.debug(f"Could not format column {col} as datetime: {e_format}")


        if df.empty:
            app.logger.info(f"No data found for report: {report_type}")
            return no_update, dbc.Alert(f"No data found for report: {report_type}.", color="info", dismissable=True, duration=4000)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.csv"

        app.logger.info(f"Preparing download for file: {filename}")
        return dcc.send_data_frame(df.to_csv, filename, index=False), \
               dbc.Alert(f"Report '{filename_prefix.replace('_', ' ').title()}' generated.", color="success", dismissable=True, duration=4000)

    except psycopg2.Error as e_db:
        app.logger.error(f"Database error during report generation for {report_type}: {e_db}")
        return no_update, dbc.Alert(f"Database error generating report: {e_db}", color="danger", dismissable=True, duration=4000)
    except Exception as e_general:
        app.logger.error(f"General error during report generation for {report_type}: {e_general}")
        return no_update, dbc.Alert(f"An unexpected error occurred: {e_general}", color="danger", dismissable=True, duration=4000)
    finally:
        if conn:
            conn.close()
            app.logger.info(f"Database connection closed after report generation for {report_type}.")


# --- Main execution ---
if __name__ == '__main__':
    app.logger.info("Starting Dash application...")
    app.run(debug=True, port=8050)