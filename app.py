# app.py
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
import logging

# Import from modules
from modules.callbacks import register_callbacks

# --- Initialize Dash App ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.PULSE], suppress_callback_exceptions=True)
app.title = "Internal DB Access System"

# Configure logging
log_format = '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format) # Basic config for root logger
app.logger.setLevel(logging.INFO) # Set level for Dash app's logger

# Main App Layout (Structure for URL routing and session management)
app.layout = html.Div([
    dcc.Store(id='session-store', storage_type='session'),
    dcc.Store(id='refresh-trigger-store', data=0),
    dcc.Location(id='url', refresh=False),
    html.Div(id='app-container-wrapper') # Content will be rendered here by render_page_content callback
])

# Register all callbacks
register_callbacks(app)

# --- Main execution ---
if __name__ == '__main__':
    app.logger.info("Starting Dash application...")
    app.run(debug=True, port=8050)