# modules/layouts.py
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
from dash_iconify import DashIconify

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
                            html.Strong("Generate Reports:"), " Select a report type and download CSV files for auditing and overview."
                        ]),
                         html.Li([
                            DashIconify(icon="carbon:logout", className="me-2 text-primary"),
                            html.Strong("Logout:"), " Securely log out from the system using the button at the bottom of the sidebar."
                        ]),
                    ], style={'listStyleType': 'none', 'paddingLeft': '0', 'textAlign': 'left'}),
                    html.P("Remember to handle all data with care and follow company policies.", className="mt-4 text-muted fst-italic")
                ],
                lg=8,  # Guide takes 8/12 on large screens
                md=7,  # Guide takes 7/12 on medium screens
                sm=12, # Full width on small screens
                className="p-4", # Removed border-end for cleaner stacking
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
                            html.Div(id="login-status-message", className="mt-3 text-center")
                        ])
                    ])
                ]),
                lg=4,  # Login form takes 4/12 on large screens
                md=5,  # Login form takes 5/12 on medium screens
                sm=12,
                className="mt-4 mt-md-0" # Margin top on small/medium when stacking
            )
        ],
        align="start", # Keep columns top-aligned
        className="mt-3 gx-lg-4" # Gutter between columns on large screens
    )
], id="login-container-main", className="py-5")


# Sidebar Layout
def create_sidebar(app, session_data): # Added app parameter for logging
    user_first_name = session_data.get('first_name', 'User')
    app.logger.info(f"Creating sidebar for {user_first_name}")

    return dbc.Col([
        html.Div([
            html.H2("Internal DB Access", className="sidebar-title"),
            html.P(f"Welcome, {user_first_name}!", style={'textAlign': 'left', 'marginBottom': '20px', 'paddingLeft': '10px'})
        ], className="sidebar-header"),

        dbc.Button([DashIconify(icon="carbon:add-alt", className="me-2"), "New Access Request"],
                   id="open-new-request-modal-button-sidebar", color="light",
                   className="sidebar-action-button mb-4"),
        html.Hr(style={'borderColor': 'rgba(255,255,255,0.2)'}),
        dbc.Nav([
            dbc.NavLink([DashIconify(icon="carbon:table-of-contents", className="me-2"), "My Requests"], href="#my-requests", active="exact", className="mb-1"),
            dbc.NavLink([DashIconify(icon="carbon:checkbox-checked", className="me-2"), "Approval Queue"], href="#approvals", active="exact", className="mb-1", id="navlink-approvals", style={'display': 'block' if session_data.get('is_manager') else 'none'}),
            dbc.NavLink([DashIconify(icon="carbon:report", className="me-2"), "Generate Reports"], href="#reports", active="exact"),
        ], vertical=True, pills=False, id="sidebar-nav"),

        dbc.Button([DashIconify(icon="carbon:logout", className="me-2"), "Logout"],
                   id="sidebar-logout-button", color="secondary", outline=True, className="mt-auto")
    ], id="sidebar-column", width="auto")

# Main Content Area Layout (for the dashboard)
def create_main_content_area(app, session_data): # Added app parameter for logging
    is_manager = session_data.get('is_manager', False)
    app.logger.info(f"Creating main content area. Is manager: {is_manager}")

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
        dbc.CardHeader(html.H4("My Access Requests", className="mb-0"), id="my-requests"),
        dbc.CardBody([
            dash_table.DataTable(
                id='my-requests-table',
                style_cell={'textAlign': 'left', 'padding': '10px', 'whiteSpace': 'normal', 'height': 'auto', 'minWidth': '120px'},
                style_header={'fontWeight': '600', 'backgroundColor': '#e9ecef'},
                style_table={'overflowX': 'auto'},
                page_size=10, row_selectable='single', selected_rows=[],
            ),
            html.Div(id='my-request-action-panel', className="mt-3 p-3", style={'display': 'none'})
        ])
    ])

    # Always include the approval_section_ui structure, but control visibility with CSS
    approval_section_ui = dbc.Card([
        dbc.CardHeader(html.H4("Requests Requiring My Action / History", className="mb-0"), id="approvals"),
        dbc.CardBody([
            dash_table.DataTable(
                id='approval-requests-table',
                style_cell={'textAlign': 'left', 'padding': '10px', 'whiteSpace': 'normal', 'height': 'auto', 'minWidth': '120px'},
                style_header={'fontWeight': '600', 'backgroundColor': '#e9ecef'},
                style_table={'overflowX': 'auto'}, # Default style
                page_size=5, row_selectable='single', selected_rows=[],
            ),
            html.Div(id='approval-action-panel', className="mt-3 p-3", style={'display': 'none'}) # Default to hidden
        ])
    ], id="approval-section-card", style={'display': 'block' if is_manager else 'none'}) # Card visibility

    reports_section_ui = dbc.Card([
        dbc.CardHeader(html.H4("Generate Reports", className="mb-0"), id="reports"),
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
    ])

    return dbc.Col([
        dcc.Interval(id='dashboard-load-trigger', interval=100, n_intervals=0, max_intervals=1),
        dcc.Store(id='selected-request-id-store'),
        dcc.Store(id='selected-approval-request-id-store'),
        html.Div(id='action-feedback-alert-placeholder', className="mb-3"),
        new_request_modal,
        my_requests_section_ui,
        approval_section_ui, # Always include this
        reports_section_ui
    ], id="page-content")