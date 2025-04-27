# app.py
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
import layouts
import callbacks # Import to register callbacks

# --- App Initialization ---
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True, # Needed because layout changes
    title="Access Request System"
)
server = app.server # Expose server variable for deployment

# --- App Layout ---
app.layout = html.Div([
    # Store for user session info (replace with proper session management in production)
    dcc.Store(id='user-store', storage_type='session'), # 'session' persists across page reloads
    dcc.Store(id='request-id-store', storage_type='memory'), # Temp store for modal

    # Navbar (updated by callback)
    html.Div(id='navbar-div', children=layouts.create_navbar(None)),

    # Page content (updated by callback based on login)
    html.Div(id='page-content', children=layouts.create_login_layout())
])

# --- Register Callbacks ---
# This function call finds and registers all functions decorated with @app.callback in callbacks.py
callbacks.register_callbacks(app)

# --- Run the App ---
if __name__ == '__main__':
    # Ensure DB utils can connect before starting
    conn_test = db_utils.get_db_connection()
    if conn_test:
        print("Database connection successful.")
        conn_test.close()
        app.run_server(debug=True, port=8051) # Use a different port if 8050 is busy
    else:
        print("Database connection failed. Please check config.py and ensure PostgreSQL is running.")
        print("Application will not start.")