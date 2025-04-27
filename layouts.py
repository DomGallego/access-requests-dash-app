# layouts.py
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table

# --- Reusable Components ---
def create_navbar(user_info):
    """Creates the top navigation bar."""
    if not user_info:
        return dbc.NavbarSimple(brand="Database Access Request System", color="primary", dark=True)

    logout_button = dbc.Button("Logout", id="logout-button", color="secondary", className="ml-auto")
    welcome_msg = f"Welcome, {user_info.get('name', 'User')} ({user_info.get('role', '')})"

    return dbc.NavbarSimple(
        brand="Database Access Request System",
        children=[
            dbc.NavItem(dbc.NavLink(welcome_msg, disabled=True)),
            dbc.NavItem(logout_button),
        ],
        color="primary",
        dark=True,
        fluid=True, # Use fluid for better spacing with button on right
    )


# --- Layout Functions ---

def create_login_layout():
    """Layout for the login screen."""
    return dbc.Container([
        dbc.Row(dbc.Col(html.H2("Login"), width=12), className="mb-3"),
        dbc.Row(dbc.Col(dbc.Input(id="user-id-input", placeholder="Enter Your User ID (e.g., 101, 201)", type="text"), width=6)),
        dbc.Row(dbc.Col(dbc.Button("Login", id="login-button", color="primary"), width=6), className="mt-3"),
        dbc.Row(dbc.Col(html.Div(id="login-feedback"), width=6), className="mt-3") # For error messages
    ], fluid=True, className="mt-5")


def create_requestor_layout(employee_id):
    """Layout for the requestor dashboard."""
    my_requests_table = dash_table.DataTable(
        id='my-requests-table',
        columns=[
            {"name": "Req ID", "id": "request_id"},
            {"name": "Table Name", "id": "table_name"},
            {"name": "Role", "id": "requested_role"},
            {"name": "Status", "id": "status"},
            {"name": "Request Date", "id": "request_date"},
            {"name": "Decision Date", "id": "decision_date"},
            {"name": "Approver", "id": "approver_name"},
            {"name": "Comments", "id": "approver_comments", 'type': 'text', 'presentation': 'markdown'}, # Allow longer text
            {"name": "Justification", "id": "justification", 'type': 'text', 'presentation': 'markdown'},
        ],
        data=[], # Populated by callback
        style_cell={'textAlign': 'left', 'padding': '5px', 'minWidth': '100px', 'width': '150px', 'maxWidth': '300px', 'whiteSpace': 'normal', 'height': 'auto'},
        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
        page_size=10,
        sort_action="native",
        filter_action="native",
        tooltip_data=[ # Show full text on hover
            {'column': 'justification', 'value': row['justification'], 'type': 'markdown'}
            for row in dash_table.DataTable(id='my-requests-table').data # Placeholder, data comes from callback
        ] if dash_table.DataTable(id='my-requests-table').data else [],
        tooltip_duration=None,
    )

    return dbc.Container([
        dbc.Row(dbc.Col(dbc.Button("Submit New Access Request", id="new-request-button", color="success"), width=12), className="mb-3"),
        dbc.Row(dbc.Col(html.H4("My Access Requests"), width=12), className="mb-2"),
        dbc.Row(dbc.Col(my_requests_table, width=12)),
        # Div for the new request form (initially hidden or separate)
        html.Div(id='new-request-form-div', style={'display': 'none'}, children=[
             html.Hr(),
             html.H4("New Access Request Form"),
             dbc.Form([
                 dbc.Row([
                     dbc.Label("Database Table", width=2),
                     dbc.Col(dcc.Dropdown(id='db-table-dropdown', options=[], placeholder="Select Table..."), width=10)
                 ], className="mb-3"),
                 dbc.Row([
                     dbc.Label("Access Role", width=2),
                     dbc.Col(dcc.Dropdown(id='access-role-dropdown', options=[], placeholder="Select Role..."), width=10)
                 ], className="mb-3"),
                 dbc.Row([
                     dbc.Label("Justification", width=2),
                     dbc.Col(dbc.Textarea(id='justification-input', placeholder="Explain why you need this access...", required=True, style={'height': '100px'}), width=10)
                 ], className="mb-3"),
                 dbc.Button("Submit Request", id="submit-request-button", color="primary"),
                 html.Div(id="submit-feedback", className="mt-3") # For success/error messages
             ])
        ])
    ], fluid=True, className="mt-4")


def create_approver_layout(manager_id):
    """Layout for the approver dashboard."""
    pending_requests_table = dash_table.DataTable(
        id='pending-requests-table',
        columns=[
            # Hidden column to store request_id easily
            # {"name": "Req ID", "id": "request_id"},
            {"name": "Requester", "id": "requester_name"},
            {"name": "Table Name", "id": "table_name"},
            {"name": "Role", "id": "requested_role"},
            {"name": "Request Date", "id": "request_date"},
            {"name": "Justification", "id": "justification", 'type': 'text', 'presentation': 'markdown'},
            {"name": "Action", "id": "action", "presentation": "markdown"} # Use markdown for buttons
        ],
        data=[], # Populated by callback
        style_cell={'textAlign': 'left', 'padding': '5px', 'minWidth': '100px', 'width': '150px', 'maxWidth': '300px', 'whiteSpace': 'normal', 'height': 'auto'},
        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
        markdown_options={"html": True}, # Allow HTML in markdown for buttons
        page_size=10,
        sort_action="native",
         tooltip_data=[ # Show full text on hover
            {'column': 'justification', 'value': row['justification'], 'type': 'markdown'}
            for row in dash_table.DataTable(id='pending-requests-table').data # Placeholder, data comes from callback
        ] if dash_table.DataTable(id='pending-requests-table').data else [],
        tooltip_duration=None,
        # row_selectable='single', # Alternative way to select row
    )

    return dbc.Container([
        dbc.Row(dbc.Col(html.H4("Pending Access Requests for Approval"), width=12), className="mb-2"),
        dbc.Row(dbc.Col(pending_requests_table, width=12)),
        # Modal for displaying details and taking action
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Review Access Request"), id="approval-modal-title"),
                dbc.ModalBody(id="approval-modal-body"), # Content populated by callback
                dbc.ModalFooter([
                    dbc.Input(id="approver-comments-input", placeholder="Add comments (mandatory if rejecting)", type="text", className="mb-2"),
                    dbc.Button("Approve", id="approve-button", color="success", className="mr-1"),
                    dbc.Button("Reject", id="reject-button", color="danger"),
                    # dbc.Button("Cancel", id="cancel-button", color="secondary") # Close handled by modal toggle
                ]),
            ],
            id="approval-modal",
            is_open=False, # Initially hidden
            size="lg", # Larger modal
        ),
         html.Div(id="approval-feedback", className="mt-3") # For success/error messages
    ], fluid=True, className="mt-4")