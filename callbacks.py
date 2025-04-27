# callbacks.py
from dash import Input, Output, State, callback, html, dcc, no_update, ctx # ctx helps identify trigger
import dash_bootstrap_components as dbc
import layouts
import db_utils
from config import SIMULATED_USERS # Import simulated user data

def register_callbacks(app):

    # --- Login/Logout and Page Routing ---
    @app.callback(
        Output('page-content', 'children'),
        Output('navbar-div', 'children'),
        Output('user-store', 'data'), # Store user info
        Output('login-feedback', 'children'), # For login errors
        Input('login-button', 'n_clicks'),
        Input('logout-button', 'n_clicks'),
        State('user-id-input', 'value'),
        State('user-store', 'data'), # Get current user state
        prevent_initial_call=True
    )
    def handle_login_logout(login_clicks, logout_clicks, user_id_input, user_data):
        triggered_id = ctx.triggered_id

        if triggered_id == 'logout-button' or not user_id_input and triggered_id == 'login-button':
            # Logout or invalid login attempt
            return layouts.create_login_layout(), layouts.create_navbar(None), None, None

        if triggered_id == 'login-button' and user_id_input:
            user_info = SIMULATED_USERS.get(user_id_input)
            if user_info:
                # Successful Login simulation
                navbar = layouts.create_navbar(user_info)
                if user_info['role'] == 'requestor':
                    layout = layouts.create_requestor_layout(user_info['employee_id'])
                elif user_info['role'] == 'approver':
                    layout = layouts.create_approver_layout(user_info['employee_id'])
                else:
                    layout = html.Div("Unknown user role.") # Fallback
                return layout, navbar, user_info, None # Clear feedback on success
            else:
                # Failed login
                feedback = dbc.Alert("Invalid User ID", color="danger")
                return layouts.create_login_layout(), layouts.create_navbar(None), None, feedback

        # If no relevant button was clicked, don't update
        return no_update, no_update, user_data, no_update


    # --- Requestor Callbacks ---

    @app.callback(
        Output('new-request-form-div', 'style'),
        Output('new-request-button', 'children'),
        Input('new-request-button', 'n_clicks'),
        State('new-request-form-div', 'style'),
        prevent_initial_call=True
    )
    def toggle_new_request_form(n_clicks, current_style):
        if n_clicks % 2 == 1: # Odd clicks: show form
            new_style = {'display': 'block'}
            button_text = "Cancel New Request"
        else: # Even clicks: hide form
            new_style = {'display': 'none'}
            button_text = "Submit New Access Request"
        return new_style, button_text

    @app.callback(
        Output('db-table-dropdown', 'options'),
        Output('access-role-dropdown', 'options'),
        Input('new-request-button', 'n_clicks'), # Trigger when form is potentially opened
        State('new-request-form-div', 'style') # Check if form is visible
    )
    def populate_request_dropdowns(n_clicks, form_style):
        # Only populate if the form is likely visible (or about to be)
        if n_clicks is not None and n_clicks > 0 and form_style.get('display') != 'none':
            table_options = db_utils.get_db_tables()
            role_options = db_utils.get_access_roles()
            return table_options, role_options
        return no_update, no_update # Don't update if form isn't shown

    @app.callback(
        Output('submit-feedback', 'children'),
        Output('my-requests-table', 'data', allow_duplicate=True), # Update table after submit
        # Clear form on successful submission
        Output('db-table-dropdown', 'value'),
        Output('access-role-dropdown', 'value'),
        Output('justification-input', 'value'),
        Input('submit-request-button', 'n_clicks'),
        State('user-store', 'data'),
        State('db-table-dropdown', 'value'),
        State('access-role-dropdown', 'value'),
        State('justification-input', 'value'),
        prevent_initial_call=True
    )
    def handle_submit_request(n_clicks, user_info, table_id, role_id, justification):
        if not user_info:
            return dbc.Alert("User not logged in.", color="danger"), no_update, no_update, no_update, no_update

        requester_id = user_info.get('employee_id')
        manager_id = user_info.get('manager_id') # Get manager from simulated data

        # Basic validation
        if not all([requester_id, table_id, role_id, justification, manager_id]):
             missing = [field for field, value in {'Table': table_id, 'Role': role_id, 'Justification': justification, 'Manager Info': manager_id}.items() if not value]
             return dbc.Alert(f"Please fill in all fields. Missing: {', '.join(missing)}", color="warning"), no_update, no_update, no_update, no_update

        success = db_utils.submit_new_request(requester_id, table_id, role_id, justification, manager_id)

        if success:
            feedback = dbc.Alert("Request submitted successfully!", color="success")
            # Refresh the requestor's table data
            my_requests_data = db_utils.get_my_requests(requester_id).to_dict('records')
            # Clear the form fields
            return feedback, my_requests_data, None, None, ""
        else:
            feedback = dbc.Alert("Failed to submit request. Please check logs or try again.", color="danger")
            return feedback, no_update, no_update, no_update, no_update


    @app.callback(
        Output('my-requests-table', 'data'),
        Input('user-store', 'data'), # Trigger when user logs in/state changes
        Input('submit-feedback', 'children') # Also refresh if a submission happens
    )
    def load_my_requests(user_info, submit_feedback):
        if user_info and user_info.get('role') == 'requestor':
            employee_id = user_info.get('employee_id')
            df = db_utils.get_my_requests(employee_id)
            return df.to_dict('records')
        return [] # Return empty list if not a requestor or not logged in


    # --- Approver Callbacks ---

    @app.callback(
        Output('pending-requests-table', 'data'),
        Input('user-store', 'data'), # Trigger on login
        Input('approval-feedback', 'children') # Trigger after approve/reject
    )
    def load_pending_approvals(user_info, approval_feedback):
        if user_info and user_info.get('role') == 'approver':
            manager_id = user_info.get('employee_id')
            df = db_utils.get_pending_approvals(manager_id)

            # Add 'Action' button column - IMPORTANT: USE UNIQUE IDs if possible
            # For simplicity here, we embed request_id in button id (less robust)
            df['action'] = [f'<button id="review-btn-{row["request_id"]}" class="btn btn-sm btn-info review-button" data-requestid="{row["request_id"]}">Review</button>' for index, row in df.iterrows()]
            return df.to_dict('records')
        return []

    # Callback to handle opening the modal
    # This uses pattern matching if we had unique IDs per row button
    # Simpler approach: Use a general listener and client-side callback later if needed
    # For now, use a less robust approach: find which button was clicked via ctx
    @app.callback(
        Output('approval-modal', 'is_open'),
        Output('approval-modal-body', 'children'),
        Output('approval-modal-title', 'children'),
        Output('request-id-store', 'data'), # Store the request ID being reviewed
        Input({'type': 'review-button', 'index': ALL}, 'n_clicks'), # Placeholder - needs actual pattern matching
        # Fallback using generic input - less reliable if table refreshes
        # Input('pending-requests-table', 'active_cell'), # Another way if row selectable
        [Input(f"review-btn-{i}", "n_clicks") for i in range(1, 100)], # HACK: Listen to potential button IDs - IMPROVE THIS!
        State('pending-requests-table', 'data'),
        prevent_initial_call=True
    )
    def open_approval_modal(*args):
        # *args captures all button clicks and the table data
        # This is complex because Dash doesn't easily tell which button IN the table was clicked without pattern matching IDs
        # Find which button was clicked using ctx.triggered_id
        triggered_id_str = ctx.triggered_id
        table_data = args[-1] # Last argument is the State

        if not triggered_id_str or not isinstance(triggered_id_str, str) or "review-btn-" not in triggered_id_str:
             return no_update, no_update, no_update, no_update

        try:
            # Extract request_id from the button ID
            request_id = int(triggered_id_str.split('-')[-1])
        except:
            return no_update, no_update, no_update, no_update # Ignore if parsing fails

        details = db_utils.get_request_details(request_id)

        if details:
            modal_body = html.Div([
                html.Strong("Requester: "), html.Span(f"{details['requester_name']} ({details['requester_email']}, Dept: {details['requester_dept']})"), html.Br(),
                html.Strong("Table Requested: "), html.Span(details['table_name']), html.Br(),
                html.I(details.get('table_description', 'No description')), html.Br(),
                html.Strong("Role Requested: "), html.Span(details['requested_role']), html.Br(),
                html.I(details.get('role_description', '')), html.Br(),
                html.Strong("Request Date: "), html.Span(details['request_date']), html.Br(),
                html.Strong("Justification:"), html.P(details['justification'], style={'whiteSpace': 'pre-wrap'}),
                html.Strong("Current Status: "), html.Span(details['status']), html.Br(),
            ])
            modal_title = f"Review Access Request #{request_id}"
            return True, modal_body, modal_title, {'request_id': request_id} # Open modal and store ID
        else:
            # Handle case where details aren't found (maybe request was already processed?)
            return False, "Could not load request details.", "Error", no_update


    # Callback to handle approve/reject actions
    @app.callback(
        Output('approval-feedback', 'children'),
        Output('approval-modal', 'is_open', allow_duplicate=True), # Close modal
        Output('pending-requests-table', 'data', allow_duplicate=True), # Refresh table
        Input('approve-button', 'n_clicks'),
        Input('reject-button', 'n_clicks'),
        State('approver-comments-input', 'value'),
        State('request-id-store', 'data'), # Get request_id from store
        State('user-store', 'data'), # Get approver's user info
        prevent_initial_call=True
    )
    def handle_approval_action(approve_clicks, reject_clicks, comments, stored_request_id, user_info):
        triggered_id = ctx.triggered_id
        request_id = stored_request_id.get('request_id') if stored_request_id else None
        approver_id = user_info.get('employee_id') if user_info else None

        if not request_id or not approver_id:
            return dbc.Alert("Error: Missing request or user information.", color="danger"), no_update, no_update

        new_status = None
        feedback = None
        success = False

        if triggered_id == 'approve-button':
            new_status = 'Approved'
            success = db_utils.update_request_status(request_id, approver_id, new_status, comments)
            if success:
                feedback = dbc.Alert(f"Request #{request_id} Approved.", color="success")
            else:
                feedback = dbc.Alert(f"Failed to approve Request #{request_id}.", color="danger")

        elif triggered_id == 'reject-button':
            new_status = 'Rejected'
            if not comments: # Mandatory comment for rejection
                 return dbc.Alert("Rejection requires comments.", color="warning"), no_update, no_update # Keep modal open
            success = db_utils.update_request_status(request_id, approver_id, new_status, comments)
            if success:
                feedback = dbc.Alert(f"Request #{request_id} Rejected.", color="success")
            else:
                feedback = dbc.Alert(f"Failed to reject Request #{request_id}.", color="danger")

        # Refresh pending table data after action
        new_pending_data = []
        if success and user_info and user_info.get('role') == 'approver':
             df = db_utils.get_pending_approvals(user_info['employee_id'])
             # Regenerate action buttons
             df['action'] = [f'<button id="review-btn-{row["request_id"]}" class="btn btn-sm btn-info review-button" data-requestid="{row["request_id"]}">Review</button>' for index, row in df.iterrows()]
             new_pending_data = df.to_dict('records')

        return feedback, False, new_pending_data # Return feedback, close modal, update table