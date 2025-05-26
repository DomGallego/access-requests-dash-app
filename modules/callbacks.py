# modules/callbacks.py
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ctx, dash_table, ALL, no_update
import psycopg2
import psycopg2.extras # For dictionary cursor
from datetime import datetime # For formatting dates
import pandas as pd # For CSV generation
import urllib.parse # For parsing query strings
import re # For email validation

# Import helpers from other modules
from .db import get_db_connection
from .layouts import login_layout, create_sidebar, create_main_content_area, create_signup_layout


def format_datetime_column(dt_obj):
    return dt_obj.strftime('%Y-%m-%d %H:%M:%S') if isinstance(dt_obj, datetime) else dt_obj

def generate_tooltip_data(df):
    if df.empty:
        return []
    return [
        {
            column: {'value': str(value), 'type': 'markdown'}
            for column, value in row.items()
        } for row in df.to_dict('records')
    ]

def register_callbacks(app):
    @app.callback(
        Output('app-container-wrapper', 'children'),
        [Input('url', 'pathname'), Input('url', 'search'), Input('session-store', 'data')]
    )
    def render_page_content(pathname, search, session_data):
        session_data = session_data or {}
        is_logged_in = session_data.get('logged_in', False)
        app.logger.info(f"render_page_content: pathname={pathname}, search={search}, is_logged_in={is_logged_in}")

        if pathname.startswith('/signup'):
            manager_email = None
            manager_name = "N/A" # Default if manager not found or direct signup
            if search:
                query_params = urllib.parse.parse_qs(search.lstrip('?'))
                manager_email = query_params.get('manager_email', [None])[0]
                if manager_email:
                    app.logger.info(f"Signup page requested with manager_email: {manager_email}")
                    conn = get_db_connection(app)
                    if conn:
                        try:
                            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                                cur.execute("SELECT first_name, last_name FROM Employees WHERE email = %s AND is_manager = TRUE", (manager_email,))
                                manager_record = cur.fetchone()
                                if manager_record:
                                    manager_name = f"{manager_record['first_name']} {manager_record['last_name']}"
                                else: # Manager not found or not a manager
                                    app.logger.warning(f"Inviting manager {manager_email} not found/not a manager. Proceeding as direct manager signup.")
                                    manager_email = None # Invalidate for subordinate signup logic
                        except Exception as e:
                            app.logger.error(f"Error fetching manager details for signup: {e}")
                            manager_email = None
                        finally:
                            if conn: conn.close()
            return create_signup_layout(app, manager_email, manager_name)

        if is_logged_in:
            section_from_url = None # Default if no section in URL
            if pathname == '/dashboard' and search: # Check for query params like ?section=approvals
                query_params = urllib.parse.parse_qs(search.lstrip('?'))
                section_from_url = query_params.get('section', [None])[0]
                app.logger.info(f"Dashboard requested with section: {section_from_url}")
            elif pathname == '/' or pathname == '/login': # Redirect to dashboard if logged in
                 app.logger.info(f"User logged in, redirecting from {pathname} to /dashboard")
                 return dcc.Location(pathname="/dashboard", id="redirect-to-dashboard")

            # Always render the full dashboard structure. The 'section_from_url' is passed
            # to potentially highlight or scroll, but not to hide other components.
            return html.Div([
                create_sidebar(app, session_data),
                create_main_content_area(app, session_data, section=section_from_url)
            ], id="app-container", className="d-flex vh-100")

        # If not logged in and not signup, show login page
        return login_layout
    # ... (rest of the callbacks remain the same as your last provided version)
    @app.callback(
        [Output('session-store', 'data', allow_duplicate=True),
         Output('login-status-message', 'children'),
         Output('url', 'pathname', allow_duplicate=True)],
        [Input('login-button', 'n_clicks')],
        [State('username-input', 'value'), State('password-input', 'value')],
        prevent_initial_call=True
    )
    def handle_login(n_clicks, username, password):
        app.logger.info(f"handle_login: n_clicks={n_clicks}, username={username}")
        if not n_clicks: return dash.no_update, "", dash.no_update
        if not username or not password: return {}, dbc.Alert("Username and password are required.", color="warning"), dash.no_update

        conn = get_db_connection(app)
        if not conn: return {}, dbc.Alert("Database connection error. Please try again later.", color="danger"), dash.no_update

        session_data_to_set, login_message, redirect_path = {}, "", dash.no_update
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT uc.employee_id, e.first_name, e.last_name, uc.password_text, e.is_manager, e.email FROM UserCredentials uc JOIN Employees e ON uc.employee_id = e.employee_id WHERE uc.username = %s;", (username,))
                user_record = cur.fetchone()
                if user_record:
                    if user_record['password_text'] == password: # Insecure, for MVP only
                        session_data_to_set = {'logged_in': True, 'employee_id': user_record['employee_id'], 'first_name': user_record['first_name'], 'last_name': user_record['last_name'], 'email': user_record['email'], 'is_manager': user_record['is_manager']}
                        app.logger.info(f"Login successful for user: {username}, employee_id: {user_record['employee_id']}")
                        redirect_path = '/dashboard' # Default redirect
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
        [Input('sidebar-logout-button', 'n_clicks')],
        prevent_initial_call=True
    )
    def handle_logout_sidebar(n_clicks_logout):
        app.logger.info(f"handle_logout_sidebar: n_clicks_logout={n_clicks_logout}")
        if n_clicks_logout and n_clicks_logout > 0:
            app.logger.info("User logged out via sidebar button.")
            return {}, '/login' # Clear session, redirect to login
        return dash.no_update, dash.no_update

    @app.callback(
        [Output('my-requests-table', 'data'), Output('my-requests-table', 'columns'),
         Output('my-requests-table', 'tooltip_data'),
         Output('my-requests-table', 'selected_rows', allow_duplicate=True)],
        [Input('dashboard-load-trigger', 'n_intervals'), Input('refresh-trigger-store', 'data')],
        [State('session-store', 'data')],
        prevent_initial_call=True
    )
    def update_my_requests_table(n_intervals_load, refresh_trigger, session_data):
        triggered_input = ctx.triggered_id
        app.logger.info(f"update_my_requests_table triggered by: {triggered_input}")
        session_data = session_data or {}
        if not (session_data.get('logged_in')):
            app.logger.info(f"update_my_requests_table: Conditions not met (not logged in).")
            return [], [], [], []
        employee_id = session_data.get('employee_id')
        app.logger.info(f"update_my_requests_table: Fetching requests for employee_id: {employee_id}")

        conn = get_db_connection(app)
        if not conn: return [], [], [], []

        data = []
        columns = [{"name": c, "id": i} for c, i in [
            ("Req ID", "request_id"), ("Table", "table_full_name"), ("Role", "requested_role"),
            ("Justification", "justification"), ("Requested", "request_date_str"), ("Status", "status"),
            ("Approver", "approver_display_name"), # Simplified to one "Approver" column
            ("Decided", "decision_date_str"), ("Comments", "approver_comments")
        ]]
        df_for_tooltip = pd.DataFrame()

        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT ar.request_id, ar.requester_id, dt.schema_name || '.' || dt.table_name AS table_full_name,
                           aro.role_name AS requested_role, ar.justification, ar.request_date, ar.status,
                           ar.decision_date, ar.approver_comments,
                           CASE
                               WHEN ar.status = 'Pending' THEN
                                   CASE
                                       WHEN req_emp_details.is_manager = TRUE AND req_emp_details.manager_id IS NULL THEN 'System Admin'
                                       WHEN req_emp_details.manager_id IS NOT NULL THEN manager_of_requester.first_name || ' ' || manager_of_requester.last_name
                                       ELSE 'N/A (Pending Config)'
                                   END
                               WHEN ar.approver_id IS NOT NULL THEN actual_approver_emp.first_name || ' ' || actual_approver_emp.last_name
                               ELSE 'N/A'
                           END AS approver_display_name
                    FROM AccessRequests ar
                    JOIN DatabaseTables dt ON ar.table_id = dt.table_id
                    JOIN AccessRoles aro ON ar.requested_role_id = aro.role_id
                    JOIN Employees req_emp_details ON ar.requester_id = req_emp_details.employee_id
                    LEFT JOIN Employees manager_of_requester ON req_emp_details.manager_id = manager_of_requester.employee_id
                    LEFT JOIN Employees actual_approver_emp ON ar.approver_id = actual_approver_emp.employee_id
                    WHERE ar.requester_id = %s ORDER BY ar.request_date DESC;
                """, (employee_id,))
                records = cur.fetchall()
                for rec in records:
                    row = dict(rec)
                    if row.get('approver_display_name') is None:
                        row['approver_display_name'] = 'N/A'
                    row['request_date_str'] = format_datetime_column(row.get('request_date'))
                    row['decision_date_str'] = format_datetime_column(row.get('decision_date'))
                    data.append(row)
                df_for_tooltip = pd.DataFrame(data)
                app.logger.info(f"update_my_requests_table: Found {len(data)} requests for employee_id: {employee_id}")
        except Exception as e:
            app.logger.error(f"Error in update_my_requests_table: {e}")
            data = []
            df_for_tooltip = pd.DataFrame()
        finally:
            if conn: conn.close(); app.logger.info("DB connection closed after update_my_requests_table.")

        tooltip_data_generated = generate_tooltip_data(df_for_tooltip)
        return data, columns, tooltip_data_generated, []


    @app.callback(
        [Output('approval-requests-table', 'data'), Output('approval-requests-table', 'columns'),
         Output('approval-requests-table', 'tooltip_data'),
         Output('approval-requests-table', 'style_table'), Output('approval-requests-table', 'selected_rows', allow_duplicate=True),
         Output('approval-section-card', 'style')], # Keep this to hide/show the card itself
        [Input('dashboard-load-trigger', 'n_intervals'), Input('refresh-trigger-store', 'data')],
        [State('session-store', 'data')],
        prevent_initial_call=True
    )
    def update_approval_requests_table(n_intervals_load, refresh_trigger, session_data):
        app.logger.info(f"update_approval_requests_table triggered by: {ctx.triggered_id}")
        session_data = session_data or {}
        is_manager = session_data.get('is_manager', False)
        card_style = {'display': 'block' if is_manager else 'none'}

        if not (session_data.get('logged_in') and is_manager):
            app.logger.info(f"update_approval_requests_table: Conditions not met (not logged in or not manager).")
            return [], [], [], {'overflowX': 'auto', 'display': 'none'}, [], card_style

        manager_id = session_data.get('employee_id')
        app.logger.info(f"update_approval_requests_table: Fetching requests for manager_id: {manager_id} to approve.")
        conn = get_db_connection(app)
        table_style_visible = {'overflowX': 'auto', 'display': 'block'}

        if not conn:
            return [], [], [], table_style_visible, [], card_style

        data = []
        columns = [{"name": c, "id": i} for c, i in [
            ("Req ID", "request_id"), ("Requester", "requester_name"), ("Email", "requester_email"),
            ("Table", "table_full_name"), ("Role", "requested_role"), ("Justification", "justification"),
            ("Requested", "request_date_str"), ("Status", "status")
        ]]
        df_for_tooltip = pd.DataFrame()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Managers see PENDING requests from their direct non-manager reports.
                cur.execute("""
                    SELECT ar.request_id, req_emp.first_name || ' ' || req_emp.last_name AS requester_name,
                           req_emp.email AS requester_email, dt.schema_name || '.' || dt.table_name AS table_full_name,
                           aro.role_name AS requested_role, ar.justification, ar.request_date, ar.status
                    FROM AccessRequests ar
                    JOIN Employees req_emp ON ar.requester_id = req_emp.employee_id
                    JOIN DatabaseTables dt ON ar.table_id = dt.table_id
                    JOIN AccessRoles aro ON ar.requested_role_id = aro.role_id
                    WHERE req_emp.manager_id = %s      -- Requester is managed by the current manager
                      AND req_emp.is_manager = FALSE -- Requester is a non-manager
                      -- AND ar.status = 'Pending' -- Consider if you want to show history here or only pending
                    ORDER BY CASE ar.status WHEN 'Pending' THEN 0 ELSE 1 END, ar.request_date DESC;
                """, (manager_id,))
                records = cur.fetchall()
                for rec in records:
                    row = dict(rec)
                    row['request_date_str'] = format_datetime_column(row.get('request_date'))
                    data.append(row)
                df_for_tooltip = pd.DataFrame(data)
                app.logger.info(f"update_approval_requests_table: Found {len(data)} requests for manager_id: {manager_id} to approve.")
        except Exception as e:
            app.logger.error(f"Error in update_approval_requests_table: {e}")
            data = []
            df_for_tooltip = pd.DataFrame()
        finally:
            if conn: conn.close(); app.logger.info("DB conn closed after update_approval_requests_table.")

        tooltip_data_generated = generate_tooltip_data(df_for_tooltip)
        return data, columns, tooltip_data_generated, table_style_visible, [], card_style

    @app.callback(
        [Output('my-request-action-panel', 'children'), Output('my-request-action-panel', 'style'), Output('selected-request-id-store', 'data')],
        [Input('my-requests-table', 'selected_rows')],
        [State('my-requests-table', 'data'), State('session-store', 'data')]
    )
    def update_my_request_action_panel(selected_rows, table_data, session_data):
        if not selected_rows or not table_data: app.logger.info("My Request Action Panel: No row selected or no data."); return [], {'display': 'none'}, None
        selected_request_idx = selected_rows[0]
        if selected_request_idx >= len(table_data):
            app.logger.warning("My Request Action Panel: Selected row index out of bounds."); return [], {'display': 'none'}, None

        selected_request = table_data[selected_request_idx]
        request_id, request_status, requester_id_from_table, current_user_id = selected_request['request_id'], selected_request['status'], selected_request['requester_id'], session_data.get('employee_id')
        app.logger.info(f"My Request Action Panel: Selected request_id {request_id}, status {request_status}, requester {requester_id_from_table}, current_user {current_user_id}")
        if request_status == 'Pending' and requester_id_from_table == current_user_id:
            panel_content = [html.H5(f"Action for Request ID: {request_id}", className="mb-3"), html.P(f"Table: {selected_request['table_full_name']}, Role: {selected_request['requested_role']}"), dbc.Button("Cancel My Request", id="cancel-my-request-button", color="warning", className="mt-2")]
            return panel_content, {'display': 'block', 'border': '1px solid #ddd', 'padding': '15px', 'borderRadius': '5px', 'backgroundColor': '#f9f9f9'}, request_id
        return [], {'display': 'none'}, None

    @app.callback(
        [Output('approval-action-panel', 'children'), Output('approval-action-panel', 'style'), Output('selected-approval-request-id-store', 'data')],
        [Input('approval-requests-table', 'selected_rows')],
        [State('approval-requests-table', 'data'), State('session-store', 'data')]
    )
    def update_approval_action_panel(selected_rows, table_data, session_data):
        session_data = session_data or {}
        is_manager = session_data.get('is_manager', False)

        if not is_manager or not selected_rows or not table_data:
            app.logger.info("Approval Action Panel: Not a manager, no row selected, or no data.")
            return [], {'display': 'none'}, None

        selected_request_idx = selected_rows[0]
        if selected_request_idx >= len(table_data):
            app.logger.warning("Approval Action Panel: Selected row index out of bounds."); return [], {'display': 'none'}, None
        selected_request = table_data[selected_request_idx]


        request_id, request_status = selected_request['request_id'], selected_request.get('status', 'Pending')
        app.logger.info(f"Approval Action Panel: Selected request_id {request_id}, status {request_status}")

        panel_style = {'display': 'block', 'border': '1px solid #ddd', 'padding': '15px', 'borderRadius': '5px', 'backgroundColor': '#f9f9f9'}

        if request_status == 'Pending': # Only show action buttons for pending requests
            panel_content = [
                html.H5(f"Action for Request ID: {request_id}", className="mb-3"),
                html.P(f"Requester: {selected_request['requester_name']} ({selected_request['requester_email']})"),
                html.P(f"Table: {selected_request['table_full_name']}, Role: {selected_request['requested_role']}"),
                html.P([html.Strong("Justification: "), selected_request['justification']]),
                dbc.Textarea(id="approver-comment-input", placeholder="Comments (required for Reject)", className="mb-2", style={'minHeight': '80px'}),
                dbc.Button("Approve", id="approve-request-button", color="success", className="me-2"),
                dbc.Button("Reject", id="reject-request-button", color="danger")
            ]
        else: # Show read-only details for already decided requests from history
            conn = get_db_connection(app)
            approver_name_hist = "N/A"
            decision_date_hist = "N/A"
            comments_hist = "No comments."
            if conn:
                try:
                    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur_hist:
                        cur_hist.execute("""
                            SELECT COALESCE(e.first_name || ' ' || e.last_name, 'N/A') as approver_name,
                                   ar.decision_date, ar.approver_comments
                            FROM AccessRequests ar
                            LEFT JOIN Employees e ON ar.approver_id = e.employee_id
                            WHERE ar.request_id = %s
                        """, (request_id,))
                        hist_details = cur_hist.fetchone()
                        if hist_details:
                            approver_name_hist = hist_details['approver_name']
                            decision_date_hist = format_datetime_column(hist_details['decision_date'])
                            comments_hist = hist_details['approver_comments'] if hist_details['approver_comments'] else "No comments."
                except Exception as e_hist_detail:
                    app.logger.error(f"Error fetching history details for request {request_id}: {e_hist_detail}")
                finally:
                    if conn: conn.close()

            panel_content = [
                html.H5(f"Details for Request ID: {request_id}", className="mb-3"),
                html.P(f"Requester: {selected_request['requester_name']} ({selected_request['requester_email']})"),
                html.P(f"Table: {selected_request['table_full_name']}, Role: {selected_request['requested_role']}"),
                html.P([html.Strong("Justification: "), selected_request['justification']]),
                html.P(f"Status: {request_status}"),
                html.P(f"Decided By: {approver_name_hist}"),
                html.P(f"Decision Date: {decision_date_hist}"),
                html.P([html.Strong("Comments: "), comments_hist]),
            ]
        return panel_content, panel_style, request_id

    # --- SIGNUP CALLBACK ---
    @app.callback(
        [Output('signup-status-message', 'children'),
         Output('url', 'pathname', allow_duplicate=True)],
        [Input('signup-button', 'n_clicks')],
        [State('signup-firstname-input', 'value'), State('signup-lastname-input', 'value'),
         State('signup-email-input', 'value'), State('signup-department-dropdown', 'value'),
         State('signup-password-input', 'value'), State('signup-confirm-password-input', 'value'),
         State('signup-manager-email-store', 'data')],
        prevent_initial_call=True
    )
    def handle_signup(n_clicks, first_name, last_name, email, department, password, confirm_password, inviting_manager_email):
        app.logger.info(f"handle_signup: n_clicks={n_clicks}, email={email}, inviting_manager_email={inviting_manager_email}")
        if not n_clicks: return no_update, no_update

        if not all([first_name, last_name, email, department, password, confirm_password]):
            return dbc.Alert("All fields are required.", color="warning"), no_update
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
             return dbc.Alert("Invalid email format.", color="warning"), no_update
        if password != confirm_password:
            return dbc.Alert("Passwords do not match.", color="warning"), no_update
        if len(password) < 6:
            return dbc.Alert("Password must be at least 6 characters.", color="warning"), no_update

        conn = get_db_connection(app)
        if not conn: return dbc.Alert("Database connection error. Please try again.", color="danger"), no_update

        manager_id_for_new_employee = None
        is_manager_for_new_employee = False

        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT employee_id FROM Employees WHERE email = %s", (email,))
                if cur.fetchone():
                    return dbc.Alert("An account with this email already exists.", color="danger"), no_update

                if inviting_manager_email:
                    cur.execute("SELECT employee_id FROM Employees WHERE email = %s AND is_manager = TRUE", (inviting_manager_email,))
                    manager_record = cur.fetchone()
                    if not manager_record:
                        app.logger.error(f"Inviting manager email {inviting_manager_email} not found or is not a manager.")
                        return dbc.Alert("Invalid invitation link or inviting manager not found.", color="danger"), no_update
                    manager_id_for_new_employee = manager_record['employee_id']
                    is_manager_for_new_employee = False
                    app.logger.info(f"Subordinate signup for {email} under manager_id {manager_id_for_new_employee}")
                else:
                    is_manager_for_new_employee = True
                    manager_id_for_new_employee = None
                    app.logger.info(f"Manager signup for {email}. They will be a top-level manager.")

                cur.execute(
                    "INSERT INTO Employees (first_name, last_name, email, department, manager_id, is_manager) VALUES (%s, %s, %s, %s, %s, %s) RETURNING employee_id",
                    (first_name, last_name, email, department, manager_id_for_new_employee, is_manager_for_new_employee)
                )
                new_employee_id = cur.fetchone()['employee_id']
                cur.execute(
                    "INSERT INTO UserCredentials (employee_id, username, password_text) VALUES (%s, %s, %s)",
                    (new_employee_id, email, password)
                )
                conn.commit()
                app.logger.info(f"Successfully created new employee_id: {new_employee_id} for email: {email}")
                return dbc.Alert("Sign up successful! Please log in.", color="success"), "/login"
        except psycopg2.Error as e:
            conn.rollback()
            app.logger.error(f"Database error during signup for {email}: {e}")
            return dbc.Alert("An error occurred during sign up. Please try again.", color="danger"), no_update
        except Exception as e_gen:
            app.logger.error(f"Generic error during signup for {email}: {e_gen}")
            return dbc.Alert("An unexpected error occurred.", color="danger"), no_update
        finally:
            if conn: conn.close()
        return no_update, no_update

    @app.callback(
        Output('invite-link-display', 'value'),
        [Input('dashboard-load-trigger', 'n_intervals'), Input('url', 'href')],
        [State('session-store', 'data')]
    )
    def generate_invite_link(n_intervals, current_url_href, session_data):
        if not session_data or not session_data.get('is_manager'):
            return "Not available for non-managers"
        manager_email = session_data.get('email')
        if not manager_email:
            return "Error: Manager email not found in session."

        base_url = "http://127.0.0.1:8050" # Default for local dev
        if current_url_href:
            try:
                parsed_url = urllib.parse.urlparse(current_url_href)
                if parsed_url.scheme and parsed_url.netloc:
                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            except Exception as e:
                app.logger.warning(f"Could not parse base_url from {current_url_href}: {e}")


        invite_path = f"/signup?manager_email={urllib.parse.quote(manager_email)}"
        full_invite_link = f"{base_url}{invite_path}"
        app.logger.info(f"Generated invite link for manager {manager_email}: {full_invite_link}")
        return full_invite_link

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
        conn = get_db_connection(app)
        if not conn: return no_update, dbc.Alert("Database connection error.", color="danger", dismissable=True, duration=4000), no_update, no_update
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE AccessRequests SET status = 'Rejected', approver_id = %s, decision_date = CURRENT_TIMESTAMP, approver_comments = 'Cancelled by requester.' WHERE request_id = %s AND requester_id = %s AND status = 'Pending';", (employee_id, request_id, employee_id))
                conn.commit()
                if cur.rowcount > 0:
                    app.logger.info(f"Request {request_id} cancelled successfully by employee {employee_id}.")
                    return current_refresh_count + 1, dbc.Alert(f"Request ID {request_id} cancelled.", color="success", dismissable=True, duration=4000), {'display': 'none'}, []
                app.logger.warning(f"Failed to cancel request {request_id}. May not be pending or requester mismatch."); return no_update, dbc.Alert(f"Failed to cancel request ID {request_id}.", color="warning", dismissable=True, duration=4000), no_update, no_update
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
        session_data = session_data or {}
        if not session_data.get('is_manager'):
            app.logger.warning("handle_approval_decision triggered by non-manager. Ignoring.")
            return no_update, no_update, {'display': 'none'}, no_update

        action_button_id = None
        if "approve-request-button.n_clicks" in triggered_prop_ids and approve_clicks and approve_clicks > 0 :
            action_button_id = "approve-request-button"
        elif "reject-request-button.n_clicks" in triggered_prop_ids and reject_clicks and reject_clicks > 0:
            action_button_id = "reject-request-button"

        if not action_button_id: app.logger.info("handle_approval_decision: No relevant button click detected."); return no_update, no_update, no_update, no_update
        if not request_id: app.logger.warning("handle_approval_decision: No request_id available."); return no_update, no_update, no_update, no_update

        approver_employee_id = session_data.get('employee_id')
        action_type, new_status, final_comment = "", "", ""

        if action_button_id == 'approve-request-button':
            action_type, new_status = "approve", "Approved"
            final_comment = comment_text if comment_text else "Approved by manager."
        elif action_button_id == 'reject-request-button':
            action_type, new_status = "reject", "Rejected"
            if not comment_text:
                app.logger.warning("handle_approval_decision: Rejection attempted without comments."); return no_update, dbc.Alert("Comments are required for rejection.", color="warning", dismissable=True, duration=4000), no_update, no_update
            final_comment = comment_text

        app.logger.info(f"handle_approval_decision: Action '{action_type}' on request_id {request_id} by approver_id {approver_employee_id} with comment '{final_comment}'")
        conn = get_db_connection(app)
        if not conn: app.logger.error("handle_approval_decision: Database connection error."); return no_update, dbc.Alert("Database connection error.", color="danger", dismissable=True, duration=4000), no_update, no_update
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE AccessRequests ar
                    SET status = %s, approver_id = %s, decision_date = CURRENT_TIMESTAMP, approver_comments = %s
                    FROM Employees req_emp
                    WHERE ar.request_id = %s AND ar.status = 'Pending'
                      AND ar.requester_id = req_emp.employee_id
                      AND req_emp.manager_id = %s; 
                """, (new_status, approver_employee_id, final_comment, request_id, approver_employee_id))
                conn.commit()
                if cur.rowcount > 0:
                    app.logger.info(f"Request {request_id} {new_status.lower()} successfully by manager {approver_employee_id}.")
                    return current_refresh_count + 1, dbc.Alert(f"Request ID {request_id} has been {new_status.lower()}.", color="success", dismissable=True, duration=4000), {'display': 'none'}, []
                app.logger.warning(f"Failed to {action_type} request {request_id}. Not pending, or you are not the designated approver."); return no_update, dbc.Alert(f"Failed to {action_type} request ID {request_id}. It might not be pending or you are not the designated approver for this request.", color="warning", dismissable=True, duration=5000), no_update, no_update
        except psycopg2.Error as e:
            conn.rollback(); app.logger.error(f"DB error {action_type}ing request {request_id}: {e}")
            return no_update, dbc.Alert(f"Error {action_type}ing request {request_id}.", color="danger", dismissable=True, duration=4000), no_update, no_update
        finally:
            if conn: conn.close(); app.logger.info("DB conn closed after handle_approval_decision.")
        return no_update, no_update, no_update, no_update

    @app.callback(
        [Output('new-request-modal', 'is_open', allow_duplicate=True),
         Output('new-request-table-dropdown', 'options'),
         Output('new-request-role-dropdown', 'options'),
         Output('new-request-table-dropdown', 'value', allow_duplicate=True),
         Output('new-request-role-dropdown', 'value', allow_duplicate=True),
         Output('new-request-justification-textarea', 'value', allow_duplicate=True),
         Output('new-request-form-feedback', 'children', allow_duplicate=True)],
        [Input('open-new-request-modal-button-sidebar', 'n_clicks'),
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

        if triggered_id == 'open-new-request-modal-button-sidebar' and n_open:
            app.logger.info("toggle_and_populate_new_request_modal: Opening modal and populating dropdowns.")
            conn = get_db_connection(app)
            if conn and session_data and session_data.get('logged_in'):
                try:
                    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                        cur.execute("SELECT table_id, schema_name || '.' || table_name AS full_name FROM DatabaseTables ORDER BY full_name;")
                        table_options = [{'label': r['full_name'], 'value': r['table_id']} for r in cur.fetchall()]
                        cur.execute("SELECT role_id, role_name FROM AccessRoles ORDER BY role_name;")
                        role_options = [{'label': r['role_name'], 'value': r['role_id']} for r in cur.fetchall()]
                except psycopg2.Error as e:
                    app.logger.error(f"DB error populating modal dropdowns: {e}")
                    modal_specific_feedback = dbc.Alert("Error loading form data. Please try again.", color="danger")
                finally:
                    if conn: conn.close()
                return True, table_options, role_options, reset_table_val, reset_role_val, reset_just_val, modal_specific_feedback
            else:
                app.logger.warning("toggle_and_populate_new_request_modal: Cannot open form. Not logged in or DB unavailable.")
                modal_specific_feedback = dbc.Alert("Cannot open form. Please ensure you are logged in and the system is available.", color="warning")
                return False, [], [], reset_table_val, reset_role_val, reset_just_val, modal_specific_feedback

        if triggered_id == 'cancel-new-request-modal-button' and n_cancel:
            app.logger.info("toggle_and_populate_new_request_modal: Closing modal via cancel button.")
            return False, dash.no_update, dash.no_update, reset_table_val, reset_role_val, reset_just_val, ""
        app.logger.debug("toggle_and_populate_new_request_modal: No relevant trigger, returning no_update.");
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
        if not n_clicks_submit: return no_update, no_update, no_update, no_update, no_update, no_update, no_update
        modal_feedback, new_refresh_count, modal_is_open = no_update, no_update, True
        global_feedback = no_update
        reset_table, reset_role, reset_justification = no_update, no_update, no_update

        if not all([table_id, role_id, justification]):
            modal_feedback = dbc.Alert("All fields are required.", color="warning", dismissable=True)
            return modal_feedback, new_refresh_count, modal_is_open, reset_table, reset_role, reset_justification, global_feedback
        if len(justification) < 20:
            modal_feedback = dbc.Alert("Justification must be at least 20 characters long.", color="warning", dismissable=True)
            return modal_feedback, new_refresh_count, modal_is_open, reset_table, reset_role, reset_justification, global_feedback
        if not session_data or not session_data.get('logged_in'):
            modal_feedback = dbc.Alert("Authentication error. Please log in again.", color="danger", dismissable=True)
            return modal_feedback, new_refresh_count, modal_is_open, reset_table, reset_role, reset_justification, global_feedback

        requester_id = session_data.get('employee_id')
        conn = get_db_connection(app)
        if not conn:
            modal_feedback = dbc.Alert("Database connection error.", color="danger", dismissable=True)
            return modal_feedback, new_refresh_count, modal_is_open, reset_table, reset_role, reset_justification, global_feedback
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO AccessRequests (requester_id, table_id, requested_role_id, justification, request_date, status) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, 'Pending') RETURNING request_id;",
                    (requester_id, table_id, role_id, justification)
                )
                new_request_id = cur.fetchone()[0]
                conn.commit()
                app.logger.info(f"New access request {new_request_id} submitted by employee {requester_id}.")
                global_feedback = dbc.Alert(f"Access request (ID: {new_request_id}) submitted successfully!", color="success", duration=5000, dismissable=True)
                new_refresh_count = current_refresh_count + 1
                modal_is_open = False; modal_feedback = ""
                reset_table, reset_role, reset_justification = None, None, ""
        except psycopg2.Error as e:
            conn.rollback(); app.logger.error(f"DB error submitting new request: {e}")
            modal_feedback = dbc.Alert(f"Error submitting request: {e}", color="danger", dismissable=True)
        except Exception as e_gen:
            app.logger.error(f"Generic error submitting new request: {e_gen}")
            modal_feedback = dbc.Alert("An unexpected error occurred.", color="danger", dismissable=True)
        finally:
            if conn: conn.close()
        return modal_feedback, new_refresh_count, modal_is_open, reset_table, reset_role, reset_justification, global_feedback


    @app.callback(
        [Output('download-csv', 'data'), Output('report-generation-feedback', 'children')],
        [Input('download-report-button', 'n_clicks')],
        [State('report-type-dropdown', 'value'), State('session-store', 'data')],
        prevent_initial_call=True
    )
    def generate_report_download(n_clicks, report_type, session_data):
        app.logger.info(f"generate_report_download: n_clicks={n_clicks}, report_type={report_type}")
        if not n_clicks: return no_update, no_update
        if not report_type:
            app.logger.warning("generate_report_download: No report type selected.")
            return no_update, dbc.Alert("Please select a report type.", color="warning", dismissable=True, duration=4000)
        conn = get_db_connection(app)
        if not conn:
            app.logger.error("generate_report_download: Database connection error.")
            return no_update, dbc.Alert("Database connection error.", color="danger", dismissable=True, duration=4000)

        query, filename_prefix, df = "", "", None
        try:
            if report_type == 'audit_log':
                filename_prefix = "access_request_audit_log"
                query = """
                SELECT ar.request_id AS "Request ID",
                       req_emp_details.first_name || ' ' || req_emp_details.last_name AS "Requester Name",
                       req_emp_details.department AS "Requester Department",
                       dt.schema_name || '.' || dt.table_name AS "Target Table",
                       aro.role_name AS "Requested Role",
                       ar.justification AS "Justification",
                       ar.request_date AS "Request Date",
                       ar.status AS "Status",
                       CASE
                           WHEN ar.status = 'Pending' THEN
                               CASE
                                   WHEN req_emp_details.is_manager = TRUE AND req_emp_details.manager_id IS NULL THEN 'System Admin'
                                   WHEN req_emp_details.manager_id IS NOT NULL THEN manager_of_requester.first_name || ' ' || manager_of_requester.last_name
                                   ELSE 'N/A (Pending Config)'
                               END
                           WHEN ar.approver_id IS NOT NULL THEN actual_approver_emp.first_name || ' ' || actual_approver_emp.last_name
                           ELSE 'N/A'
                       END AS "Approver Name",
                       ar.decision_date AS "Decision Date",
                       ar.approver_comments AS "Approver Comments"
                FROM AccessRequests ar
                JOIN Employees req_emp_details ON ar.requester_id = req_emp_details.employee_id
                JOIN DatabaseTables dt ON ar.table_id = dt.table_id
                JOIN AccessRoles aro ON ar.requested_role_id = aro.role_id
                LEFT JOIN Employees manager_of_requester ON req_emp_details.manager_id = manager_of_requester.employee_id
                LEFT JOIN Employees actual_approver_emp ON ar.approver_id = actual_approver_emp.employee_id
                ORDER BY ar.request_id DESC;
                """
            elif report_type == 'user_permissions':
                filename_prefix = "user_access_permissions_report"
                query = """
                SELECT e.first_name || ' ' || e.last_name AS "Employee Name",
                       e.email AS "Employee Email",
                       e.department AS "Employee Department",
                       dt.schema_name || '.' || dt.table_name AS "Target Table",
                       aro.role_name AS "Approved Role",
                       ar.decision_date AS "Approval Date",
                       COALESCE(app_mgr.first_name || ' ' || app_mgr.last_name, 'System Admin/N/A') AS "Approved By Name"
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
                SELECT ar.request_id AS "Request ID",
                       req_emp.first_name || ' ' || req_emp.last_name AS "Requester Name",
                       dt.schema_name || '.' || dt.table_name AS "Target Table",
                       aro.role_name AS "Requested Role", ar.request_date AS "Request Date",
                       ROUND(EXTRACT(EPOCH FROM (NOW() - ar.request_date)) / (60*60*24), 2) AS "Days Pending",
                       CASE
                           WHEN req_emp.is_manager = TRUE AND req_emp.manager_id IS NULL THEN 'System Admin'
                           WHEN req_emp.manager_id IS NOT NULL THEN mgr_emp.first_name || ' ' || mgr_emp.last_name
                           ELSE 'N/A (Error in Hierarchy)'
                       END AS "Assigned Approver"
                FROM AccessRequests ar
                JOIN Employees req_emp ON ar.requester_id = req_emp.employee_id
                JOIN DatabaseTables dt ON ar.table_id = dt.table_id
                JOIN AccessRoles aro ON ar.requested_role_id = aro.role_id
                LEFT JOIN Employees mgr_emp ON req_emp.manager_id = mgr_emp.employee_id
                WHERE ar.status = 'Pending'
                ORDER BY ar.request_date ASC;
                """
            else:
                app.logger.warning(f"generate_report_download: Unknown report type: {report_type}")
                return no_update, dbc.Alert(f"Unknown report type: {report_type}", color="danger", dismissable=True, duration=4000)

            df = pd.read_sql_query(query, conn)
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            if df.empty:
                app.logger.info(f"generate_report_download: No data found for report: {report_type}.")
                return no_update, dbc.Alert(f"No data found for report: {report_type}.", color="info", dismissable=True, duration=4000)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.csv"
            app.logger.info(f"generate_report_download: Report '{filename}' generated successfully.")
            return dcc.send_data_frame(df.to_csv, filename, index=False), dbc.Alert(f"Report '{filename_prefix.replace('_', ' ').title()}' generated.", color="success", dismissable=True, duration=4000)
        except psycopg2.Error as e_db:
            app.logger.error(f"generate_report_download: Database error generating report: {e_db}")
            return no_update, dbc.Alert(f"Database error generating report: {e_db}", color="danger", dismissable=True, duration=4000)
        except Exception as e_general:
            app.logger.error(f"generate_report_download: An unexpected error occurred: {e_general}")
            return no_update, dbc.Alert(f"An unexpected error occurred: {e_general}", color="danger", dismissable=True, duration=4000)
        finally:
            if conn: conn.close()