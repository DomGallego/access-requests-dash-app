import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ctx # ctx might not be used yet, but good to have
import psycopg2
import psycopg2.extras # For dictionary cursor

# --- Database Configuration ---
# !!! WARNING: Hardcoding credentials is not secure for production.
# Consider using environment variables or a configuration file.
DB_CONFIG = {
    "dbname": "access_request_db",  # Replace with your DB name e.g., 'gcash_access_request_db'
    "user": "postgres",      # Replace with your PostgreSQL username
    "password": "password", # Replace with your PostgreSQL password
    "host": "localhost",          # Or your DB host
    "port": "5432"                # Or your DB port
}

# --- Initialize Dash App ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "GCash DB Access Login"

# --- Helper Function for DB Connection ---
def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        return None

# --- App Layout ---
login_layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Internal Database Access Request System"), width=12), className="mb-3 mt-5 text-center"),
    dbc.Row(dbc.Col(html.H4("Login"), width=12), className="mb-4 text-center"),
    dbc.Row(
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Please enter your credentials"),
                dbc.CardBody([
                    dbc.Form([
                        # Replaced dbc.FormGroup with html.Div and applied className directly
                        html.Div([
                            dbc.Label("Username (Email)", html_for="username-input", className="form-label"),
                            dbc.Input(type="email", id="username-input", placeholder="Enter your email", required=True),
                        ], className="mb-3"), # Margin bottom for spacing
                        html.Div([
                            dbc.Label("Password", html_for="password-input", className="form-label"),
                            dbc.Input(type="password", id="password-input", placeholder="Enter your password", required=True),
                        ], className="mb-3"), # Margin bottom for spacing
                        dbc.Button("Login", id="login-button", color="primary", className="w-100 mt-3", n_clicks=0),
                        html.Div(id="login-status", className="mt-3 text-center")
                    ])
                ])
            ]),
            width={"size": 6, "offset": 3}, # Centered column
            lg={"size": 4, "offset": 4}     # Smaller on large screens
        )
    )
], fluid=True)

app.layout = html.Div([
    dcc.Store(id='session-store', storage_type='session'), # Stores session data in browser
    dcc.Location(id='url', refresh=False), # For potential future navigation
    html.Div(id='page-content', children=login_layout) # Initially show login
])

# --- Callbacks ---
@app.callback(
    [Output('session-store', 'data'),
     Output('login-status', 'children'),
     Output('url', 'pathname')], # To potentially redirect later
    [Input('login-button', 'n_clicks')],
    [State('username-input', 'value'),
     State('password-input', 'value'),
     State('session-store', 'data')]
)
def handle_login(n_clicks, username, password, session_data):
    if n_clicks == 0 or not n_clicks:
        return dash.no_update, "", dash.no_update

    session_data = session_data or {}

    if not username or not password:
        return session_data, dbc.Alert("Username and password are required.", color="warning"), dash.no_update

    conn = get_db_connection()
    if not conn:
        return session_data, dbc.Alert("Database connection error. Please try again later.", color="danger"), dash.no_update

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
                if user_record['password_text'] == password:
                    session_data = {
                        'logged_in': True,
                        'employee_id': user_record['employee_id'],
                        'first_name': user_record['first_name'],
                        'last_name': user_record['last_name'],
                        'email': user_record['email'],
                        'is_manager': user_record['is_manager']
                    }
                    welcome_message = f"Login Successful! Welcome, {user_record['first_name']} {user_record['last_name']}."
                    return session_data, dbc.Alert(welcome_message, color="success"), dash.no_update
                else:
                    return {}, dbc.Alert("Invalid username or password.", color="danger"), dash.no_update
            else:
                return {}, dbc.Alert("Invalid username or password.", color="danger"), dash.no_update
    except psycopg2.Error as e:
        print(f"Database query error: {e}")
        return {}, dbc.Alert("An error occurred during login. Please try again.", color="danger"), dash.no_update
    finally:
        if conn:
            conn.close()

# --- Main execution ---
if __name__ == '__main__':
    print("Starting Dash application...")
    print("Access it at http://127.0.0.1:8050/")
    print("---")
    print("IMPORTANT SECURITY NOTE:")
    print("This application uses plaintext password checking as per the provided database schema.")
    print("This is INSECURE and NOT SUITABLE for production environments.")
    print("In a real-world scenario, passwords must be securely hashed and salted.")
    print("---")
    app.run(debug=True, port=8050)