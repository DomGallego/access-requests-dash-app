# Internal Database Access Request System

This project is a Dash web application designed to manage internal requests for accessing database tables. It provides a user interface for employees to submit access requests, for managers to approve or reject them, and for administrators to generate reports.

## Features

*   **User Authentication:** Secure login for employees.
*   **Access Request Submission:** Users can request access to specific database tables with a chosen role and justification.
*   **Request Management (for users):** Users can view the status of their submitted requests and cancel pending ones.
*   **Approval Workflow (for managers):** Managers can view, approve, or reject access requests submitted by their team members.
*   **Reporting:** Generation of CSV reports, including:
    *   Access Request Audit Log
    *   User Access Permissions
    *   Pending Access Requests
*   **Modular Design:** The application is structured with separate modules for layouts and callbacks for better organization and maintainability.
*   **Modern UI:** Utilizes Dash Bootstrap Components and custom CSS for a clean and responsive user interface.

## Technologies Used

*   **Python:** Core programming language.
*   **Dash:** Framework for building the web application.
*   **Plotly:** Used by Dash for creating interactive UI components.
*   **Dash Bootstrap Components:** For layout and styling using Bootstrap.
*   **Dash Iconify:** For incorporating icons into the UI.
*   **PostgreSQL:** (Assumed based on `psycopg2` usage in older versions) The backend database for storing user, request, and table information.
*   **Psycopg2:** Python adapter for PostgreSQL.

## Project Structure

```
access-requests-dash-app/
├── app.py                # Main application entry point, initializes Dash app, registers callbacks
├── modules/
│   ├── __init__.py
│   ├── callbacks.py      # Contains all Dash callback logic
│   ├── database.py       # (Assumed) Handles database connections and queries
│   └── layouts.py        # Defines the layout components for different pages/sections
├── assets/
│   └── custom.css        # Custom CSS for styling the application
├── Old Versions/         # Contains previous iterations of the application code
└── README.md             # This file
```

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd access-requests-dash-app
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    (Assuming a `requirements.txt` file will be created. If not, list major dependencies like `dash`, `dash-bootstrap-components`, `psycopg2-binary`, `dash-iconify`)
    ```bash
    pip install -r requirements.txt
    ```
    Or, install manually:
    ```bash
    pip install dash dash-bootstrap-components psycopg2-binary dash-iconify pandas
    ```

4.  **Database Setup:**
    *   Ensure you have a PostgreSQL server running.
    *   Create a database (e.g., `access_request_db`).
    *   Set up the necessary tables (e.g., `Employees`, `DatabaseTables`, `AccessRoles`, `AccessRequests`). The schema can be inferred from the SQL queries in the callback files (e.g., in `Old Versions/app6.1.py` or the current `modules/callbacks.py`).
    *   Update the database connection details. In older versions, this was in `DB_CONFIG`. In the current structure, this is likely handled within `modules/database.py` or configured where `get_db_connection()` is defined.

5.  **Environment Variables (if any):**
    *   If database credentials or other sensitive information are managed via environment variables, ensure they are set.

## Running the Application

Once the setup is complete, run the main application file:

```bash
python app.py
```

The application will typically be available at `http://127.0.0.1:8050/` in your web browser.

## Configuration

*   **Database Connection:** Configure your PostgreSQL database connection details. Key details include:
    *   `dbname`
    *   `user`
    *   `password`
    *   `host`
    *   `port`

---