import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
from dash_iconify import DashIconify
import urllib.parse # For parsing query strings

# --- Login Layout ---
login_layout = dbc.Container([
    dbc.Row(
        dbc.Col(html.H1("Internal DB Access", className="display-4 fw-bold"), width=12),
        className="my-5 text-center"
    ),
    dbc.Row(
        [
            # Quick Guide Column
            dbc.Col(
                [
                    html.H4("Quick Guide", className="mb-3 text-primary"),
                    html.P("Welcome! Here’s how to use the Internal Database Access System:", className="mb-3"),
                    html.Ul([
                        html.Li([
                            DashIconify(icon="carbon:login", className="me-2 text-primary"),
                            html.Strong("Login:"), " Enter your company email and password."
                        ]),
                        html.Li([
                            DashIconify(icon="carbon:user-follow", className="me-2 text-primary"),
                            html.Strong("Sign Up:"), " Managers can sign up directly using the link below. Subordinates must use an invitation link provided by their manager."
                        ]),
                        html.Li([
                            DashIconify(icon="carbon:mouse-cursor", className="me-2 text-primary"),
                            html.Strong("Navigation:"), " Use the purple sidebar (once logged in) for all actions."
                        ]),
                        html.Li([
                            DashIconify(icon="carbon:add-alt", className="me-2 text-primary"),
                            html.Strong("New Access Request:"), " Click this button in the sidebar to request access to specific database tables. Provide clear justification."
                        ]),
                        html.Li([
                            DashIconify(icon="carbon:table-of-contents", className="me-2 text-primary"),
                            html.Strong("My Requests:"), " Track the status of your submitted requests. Click a row to see if you can cancel a pending request."
                        ]),
                        html.Li([
                            DashIconify(icon="carbon:checkbox-checked", className="me-2 text-primary"),
                            html.Strong("Approval Queue (Managers):"), " If you are a manager, this section will show requests from your team. Click a row to approve or reject."
                        ]),
                        html.Li([
                            DashIconify(icon="carbon:report", className="me-2 text-primary"),
                            html.Strong("Generate Reports (Managers):"), " Managers can select a report type and download CSV files for auditing and overview." # Updated text
                        ]),
                         html.Li([
                            DashIconify(icon="carbon:logout", className="me-2 text-primary"),
                            html.Strong("Logout:"), " Securely log out from the system using the button at the bottom of the sidebar."
                        ]),
                    ], style={'listStyleType': 'none', 'paddingLeft': '0', 'textAlign': 'left'}),
                    html.P("Remember to handle all data with care and follow company policies.", className="mt-4 text-muted fst-italic")
                ],
                lg=8, md=7, sm=12, className="p-4",
                style={'fontSize': '0.95rem', 'lineHeight': '1.6'}
            ),

            # Login Form Column
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader(html.H4("User Login", className="mb-0")),
                    dbc.CardBody([
                        dbc.Form([
                            html.Div([
                                dbc.Label("Username (Email)", html_for="username-input", className="form-label"),
                                dbc.Input(type="email", id="username-input", placeholder="your.email@example.com", required=True, size="lg"),
                            ], className="mb-3"),
                            html.Div([
                                dbc.Label("Password", html_for="password-input", className="form-label"),
                                dbc.Input(type="password", id="password-input", placeholder="Enter your password", required=True, size="lg"),
                            ], className="mb-3"),
                            dbc.Button("Login", id="login-button", color="primary", className="w-100 mt-3 py-2", n_clicks=0, size="lg"),
                            html.Div(id="login-status-message", className="mt-3 text-center"),
                            html.Div(dcc.Link("Manager Sign Up", href="/signup"), className="mt-3 text-center")
                        ])
                    ])
                ]),
                lg=4, md=5, sm=12, className="mt-4 mt-md-0"
            )
        ],
        align="start", className="mt-3 gx-lg-4"
    )
], id="login-container-main", className="py-5")


# --- Signup Layout ---
def create_signup_layout(app, manager_email=None, manager_name=None):
    app.logger.info(f"Creating signup layout. Manager email: {manager_email}, Manager name: {manager_name}")
    header_text = "Manager Sign Up"
    managed_by_info = []
    if manager_email and manager_name:
        header_text = "Subordinate Sign Up"
        managed_by_info = [
            html.Div([
                dbc.Label("Invited by Manager:", className="fw-bold"),
                html.P(f"{manager_name} ({manager_email})", className="ms-2")
            ], className="mb-3 d-flex align-items-center")
        ]

    return dbc.Container([
        dcc.Store(id='signup-manager-email-store', data=manager_email), # Store manager_email for the callback
        dbc.Row(dbc.Col(html.H1(header_text, className="display-5 fw-bold"), width=12), className="my-4 text-center"),
        dbc.Row(dbc.Col(dbc.Card([
            dbc.CardHeader(html.H4("Create Your Account", className="mb-0")),
            dbc.CardBody(
                managed_by_info +
                [dbc.Form([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("First Name", html_for="signup-firstname-input"),
                            dbc.Input(id="signup-firstname-input", type="text", placeholder="Enter first name", required=True),
                        ], md=6, className="mb-3"),
                        dbc.Col([
                            dbc.Label("Last Name", html_for="signup-lastname-input"),
                            dbc.Input(id="signup-lastname-input", type="text", placeholder="Enter last name", required=True),
                        ], md=6, className="mb-3"),
                    ]),
                    dbc.Label("Email", html_for="signup-email-input"),
                    dbc.Input(id="signup-email-input", type="email", placeholder="your.email@example.com", required=True, className="mb-3"),

                    dbc.Label("Department", html_for="signup-department-input"),
                    dcc.Dropdown(id="signup-department-dropdown",
                                 options=[
                                     {'label': 'Finance', 'value': 'Finance'},
                                     {'label': 'Operations', 'value': 'Operations'},
                                     {'label': 'Marketing', 'value': 'Marketing'},
                                     {'label': 'IT', 'value': 'IT'},
                                     {'label': 'HR', 'value': 'HR'},
                                     {'label': 'Other', 'value': 'Other'},
                                 ],
                                 placeholder="Select department",
                                 className="mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Password", html_for="signup-password-input"),
                            dbc.Input(id="signup-password-input", type="password", placeholder="Enter password", required=True),
                        ], md=6, className="mb-3"),
                        dbc.Col([
                            dbc.Label("Confirm Password", html_for="signup-confirm-password-input"),
                            dbc.Input(id="signup-confirm-password-input", type="password", placeholder="Confirm password", required=True),
                        ], md=6, className="mb-3"),
                    ]),
                    dbc.Button("Sign Up", id="signup-button", color="success", className="w-100 mt-3 py-2", n_clicks=0, size="lg"),
                    html.Div(id="signup-status-message", className="mt-3 text-center"),
                    html.Div(dcc.Link("Back to Login", href="/login"), className="mt-3 text-center"),
                ])
            ])
        ]), width={"size": 8, "offset": 2}, lg={"size": 6, "offset": 3})),
    ], className="py-5")


# --- Sidebar Layout ---
def create_sidebar(app, session_data):
    user_first_name = session_data.get('first_name', 'User')
    is_manager = session_data.get('is_manager', False) # Get manager status
    app.logger.info(f"Creating sidebar for {user_first_name}. Is manager: {is_manager}")

    nav_items = [
        dbc.NavLink([DashIconify(icon="carbon:table-of-contents", className="me-2"), "My Requests"], href="/dashboard?section=my-requests", id="navlink-my-requests", className="mb-1"),
    ]

    if is_manager:
        nav_items.extend([
            dbc.NavLink([DashIconify(icon="carbon:checkbox-checked", className="me-2"), "Approval Queue"], href="/dashboard?section=approvals", id="navlink-approvals", className="mb-1"),
            dbc.NavLink([DashIconify(icon="carbon:report", className="me-2"), "Generate Reports"], href="/dashboard?section=reports", id="navlink-reports", className="mb-1"),
            dbc.NavLink([DashIconify(icon="carbon:link", className="me-2"), "Invite Subordinate"], href="/dashboard?section=invite", id="navlink-invite", className="mb-1"),
        ])

    return dbc.Col([
        html.Div([
            html.H2("Internal DB Access", className="sidebar-title"),
            html.P(f"Welcome, {user_first_name}!", style={'textAlign': 'left', 'marginBottom': '20px', 'paddingLeft': '10px'})
        ], className="sidebar-header"),

        dbc.Button([DashIconify(icon="carbon:add-alt", className="me-2"), "New Access Request"],
                   id="open-new-request-modal-button-sidebar", color="light",
                   className="sidebar-action-button mb-4"),
        html.Hr(style={'borderColor': 'rgba(255,255,255,0.2)'}),
        dbc.Nav(nav_items, vertical=True, pills=False, id="sidebar-nav"), # Use the constructed nav_items

        dbc.Button([DashIconify(icon="carbon:logout", className="me-2"), "Logout"],
                   id="sidebar-logout-button", color="secondary", outline=True, className="mt-auto")
    ], id="sidebar-column", width="auto")

# --- Main Content Area Layout (for the dashboard) ---
def create_main_content_area(app, session_data, section=None):
    is_manager = session_data.get('is_manager', False)
    app.logger.info(f"Creating main content area. Is manager: {is_manager}. Requested section (for scroll/highlight): {section}")

    new_request_modal = dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Submit New Access Request")),
            dbc.ModalBody([
                dbc.Form([
                    dbc.Row([dbc.Col(dbc.Label("Target Database Table", html_for="new-request-table-dropdown")),], className="mb-1"),
                    dbc.Row([dbc.Col(dcc.Dropdown(id="new-request-table-dropdown", placeholder="Select Table..."),width=12)], className="mb-3"),
                    dbc.Row([dbc.Col(dbc.Label("Required Access Level", html_for="new-request-role-dropdown")),], className="mb-1"),
                    dbc.Row([dbc.Col(dcc.Dropdown(id="new-request-role-dropdown", placeholder="Select Role..."), width=12)], className="mb-3"),
                    dbc.Row([dbc.Col(dbc.Label("Justification", html_for="new-request-justification-textarea")),], className="mb-1"),
                    dbc.Row([dbc.Col(dbc.Textarea(id="new-request-justification-textarea", placeholder="Explain why you need this access (min 20 characters)", style={'minHeight': '100px'}), width=12)], className="mb-3"),
                    html.Div(id="new-request-form-feedback", className="mt-2")
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("Submit Request", id="submit-new-request-button", color="primary"),
                dbc.Button("Cancel", id="cancel-new-request-modal-button", color="secondary", className="ms-1"),
            ]),
        ],
        id="new-request-modal", is_open=False, size="lg",
    )

    my_requests_section_ui = dbc.Card([
        dbc.CardHeader(html.H4("My Access Requests", className="mb-0"), id="my-requests-header"),
        dbc.CardBody([
            dash_table.DataTable(
                id='my-requests-table',
                style_cell={'textAlign': 'left', 'padding': '10px', 'whiteSpace': 'normal', 'height': 'auto', 'minWidth': '100px', 'maxWidth': '250px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'},
                style_header={'fontWeight': '600', 'backgroundColor': '#e9ecef'},
                style_table={'overflowX': 'auto'},
                page_size=10, row_selectable='single', selected_rows=[],
                 tooltip_data=[
                    {
                        column: {'value': str(value), 'type': 'markdown'}
                        for column, value in row.items()
                    } for row in [{}]
                ],
                tooltip_duration=None,
            ),
            html.Div(id='my-request-action-panel', className="mt-3 p-3 border rounded", style={'display': 'none'})
        ])
    ], id="my-requests-section-card")

    approval_section_ui = dbc.Card([
        dbc.CardHeader(html.H4("Requests Requiring My Action / History", className="mb-0"), id="approvals-header"),
        dbc.CardBody([
            dash_table.DataTable(
                id='approval-requests-table',
                style_cell={'textAlign': 'left', 'padding': '10px', 'whiteSpace': 'normal', 'height': 'auto', 'minWidth': '100px', 'maxWidth': '200px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'},
                style_header={'fontWeight': '600', 'backgroundColor': '#e9ecef'},
                style_table={'overflowX': 'auto'},
                page_size=5, row_selectable='single', selected_rows=[],
                tooltip_data=[
                    {
                        column: {'value': str(value), 'type': 'markdown'}
                        for column, value in row.items()
                    } for row in [{}]
                ],
                tooltip_duration=None,
            ),
            html.Div(id='approval-action-panel', className="mt-3 p-3 border rounded", style={'display': 'none'})
        ])
    ], id="approval-section-card", style={'display': 'block' if is_manager else 'none'})

    # reports_section_ui is now built conditionally inside the content_to_display list
    invite_section_ui = dbc.Card([
        dbc.CardHeader(html.H4("Invite Subordinate", className="mb-0"), id="invite-header"),
        dbc.CardBody([
            html.P("Share this link with your subordinates to allow them to sign up under your management:"),
            dbc.InputGroup([
                dbc.Input(id="invite-link-display", value="Generating link...", readonly=True),
                dbc.InputGroupText(dcc.Clipboard(target_id="invite-link-display", title="Copy",
                                 className="btn btn-outline-secondary",
                                 style={'height': '100%', 'paddingTop': '0.5rem', 'paddingBottom': '0.5rem'})),
            ]),
            html.Div(id="invite-link-feedback", className="mt-2")
        ])
    ], id="invite-section-card", style={'display': 'block' if is_manager else 'none'})


    content_to_display = [my_requests_section_ui] # My Requests is always visible
    if is_manager:
        content_to_display.append(approval_section_ui)
        # Only add Reports section if the user is a manager
        reports_section_ui = dbc.Card([
            dbc.CardHeader(html.H4("Generate Reports", className="mb-0"), id="reports-header"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(dcc.Dropdown(id='report-type-dropdown',
                        options=[ {'label': 'Access Request Audit Log', 'value': 'audit_log'},
                                  {'label': 'User Access Permissions Report', 'value': 'user_permissions'},
                                  {'label': 'Pending Access Requests Report', 'value': 'pending_requests'}, ],
                        placeholder="Select a report type...", className="mb-2"
                    ), md=7),
                    dbc.Col(dbc.Button([DashIconify(icon="carbon:download", className="me-2"),"Download Report (CSV)"], id="download-report-button", color="info", className="w-100"), md=5),
                ], className="mb-3 align-items-center"),
                dcc.Download(id="download-csv"),
                html.Div(id="report-generation-feedback", className="mt-2")
            ])
        ], id="reports-section-card")
        content_to_display.append(reports_section_ui)
        content_to_display.append(invite_section_ui)


    return dbc.Col([
        dcc.Store(id='dashboard-active-section-store', data=section),
        dcc.Interval(id='dashboard-load-trigger', interval=100, n_intervals=0, max_intervals=1),
        dcc.Store(id='selected-request-id-store'),
        dcc.Store(id='selected-approval-request-id-store'),
        html.Div(id='action-feedback-alert-placeholder', className="mb-3 sticky-top", style={'zIndex': 1050}),
        new_request_modal,
    ] + content_to_display, id="page-content")