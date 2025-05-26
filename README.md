
# Internal Database Access Request System

This project is a Dash web application designed to manage internal requests for accessing database tables. It provides a user interface for employees to submit access requests, for managers to approve or reject them, and for managers to generate audit reports.

## Features

*   **User Authentication & Sign-up:**
    *   Secure login for employees and managers.
    *   **Manager Sign-up:** Managers can create accounts directly.
    *   **Subordinate Invitation:** Managers can generate unique sign-up links to invite their subordinates, automatically establishing the reporting hierarchy.
*   **Access Request Submission:** Users can request access to specific database tables with a chosen role (e.g., Read, Write) and provide a clear justification.
*   **Request Management (for users):**
    *   View the status of their submitted requests (Pending, Approved, Rejected).
    *   Cancel their own pending requests.
    *   Clearly see who the designated approver is for their pending requests (Manager or System Admin).
*   **Approval Workflow (for managers):**
    *   View a queue of pending access requests submitted by their direct non-manager reports.
    *   Approve or reject these requests with optional comments (comments are mandatory for rejection).
    *   View history of requests they have actioned.
*   **Hierarchical Approval:**
    *   Requests from regular employees go to their direct manager.
    *   Requests from managers (who are not top-level) go to their direct manager.
    *   Requests from top-level managers (who have no manager above them) are designated for "System Admin" approval (currently a conceptual state within the UI, manual backend process implied).
*   **Reporting (Manager-Specific):**
    *   Generation of CSV reports, accessible only to managers, including:
        *   Access Request Audit Log (all requests with their lifecycle details).
        *   User Access Permissions (snapshot of currently approved access).
        *   Pending Access Requests (all requests currently awaiting a decision).
*   **Modular Design:** The application is structured with separate Python modules for layouts, callbacks, and database interactions for better organization and maintainability.
*   **Modern UI:** Utilizes Dash Bootstrap Components and custom CSS for a clean, responsive, and intuitive user interface, including icons for better visual cues.

## Technologies Used

*   **Python:** Core programming language.
*   **Dash:** Framework for building the web application.
*   **Plotly:** Used by Dash for creating interactive UI components.
*   **Dash Bootstrap Components:** For layout and styling using Bootstrap.
*   **Dash Iconify:** For incorporating icons into the UI.
*   **PostgreSQL:** The backend relational database for storing employee, credentials, database table inventory, access role, and access request information.
*   **Psycopg2-binary:** Python adapter for PostgreSQL.
*   **Pandas:** Used for CSV report generation.

## Project Structure

```
internal-db-access-system/
├── app.py                # Main application entry point, initializes Dash app
├── modules/
│   ├── __init__.py
│   ├── callbacks.py      # Contains all Dash callback logic (event handling, UI updates)
│   ├── db.py             # Handles database connection (get_db_connection)
│   └── layouts.py        # Defines the layout components for login, signup, and dashboard pages
├── assets/
│   └── custom.css        # Custom CSS for styling the application
├── 01_schema_setup.sql   # SQL script to create database tables and define schema
├── 02_synthetic_data.sql # SQL script to populate the database with sample data
└── README.md             # This file
```

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd internal-db-access-system
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
    A `requirements.txt` file should ideally be provided. If not, install manually:
    ```bash
    pip install dash dash-bootstrap-components psycopg2-binary dash-iconify pandas
    ```

4.  **Database Setup:**
    *   Ensure you have a PostgreSQL server running.
    *   Create a database. The `DB_CONFIG` in `modules/db.py` assumes a database named `access_request_db`.
        ```sql
        CREATE DATABASE access_request_db;
        ```
    *   Connect to your PostgreSQL server (e.g., using `psql` or a GUI tool like pgAdmin).
    *   Execute the `01_schema_setup.sql` script against your newly created database to set up the required tables and relationships.
    *   Execute the `02_synthetic_data.sql` script to populate the tables with initial sample data for testing and demonstration.
    *   Verify the database connection details in `modules/db.py` (the `DB_CONFIG` dictionary) and adjust them if your PostgreSQL setup differs (e.g., user, password, host, port).

5.  **Environment Variables (if any):**
    *   Currently, database credentials are hardcoded in `modules/db.py` for simplicity. For a production environment, these should be managed via environment variables or a secure configuration file.

## Running the Application

Once the setup is complete and the database is populated, run the main application file from the root directory of the project:

```bash
python app.py
```

The application will typically be available at `http://127.0.0.1:8050/` in your web browser. The console will show logging output, including any errors or information about database connections and request processing.

## Using the System

1.  **Login:**
    *   Existing users (from `02_synthetic_data.sql`) can log in using their email and password (e.g., `maria.santos@gcash.example.com` / `PassMaria123!`).
2.  **Sign-up:**
    *   **Managers:** Can click the "Manager Sign Up" link on the login page to create a new top-level manager account.
    *   **Subordinates:** Must use an invitation link provided by their manager. Managers can find their "Invite Subordinate" link in the sidebar after logging in. This link will pre-fill the manager context for the subordinate's sign-up.
3.  **Requesting Access:**
    *   Click "New Access Request" in the sidebar.
    *   Fill in the target table, desired role, and a detailed justification.
4.  **Managing Requests:**
    *   **"My Requests" Table:** View all your requests and their current status. Pending requests can be cancelled.
    *   **"Approval Queue" Table (Managers Only):** View pending requests from your direct reports. Click a request to see details and action buttons (Approve/Reject).
5.  **Generating Reports (Managers Only):**
    *   Navigate to the "Generate Reports" section via the sidebar.
    *   Select a report type from the dropdown.
    *   Click "Download Report (CSV)".

## Configuration

*   **Database Connection:** The primary configuration is the `DB_CONFIG` dictionary within `modules/db.py`. Ensure this matches your PostgreSQL server setup.
    *   `dbname`: Name of the database (default: `access_request_db`)
    *   `user`: PostgreSQL username
    *   `password`: PostgreSQL password
    *   `host`: Database server host (default: `localhost`)
    *   `port`: Database server port (default: `5432`)
*   **Logging:** The application uses Python's `logging` module. The log level and format are configured in `app.py`.

---