# access-requests-dash-app


**Project Structure:**

```
dash_access_request/
├── app.py                 # Main Dash app setup and layout routing
├── callbacks.py           # All Dash callback logic
├── config.py              # Database connection details (IMPORTANT: Keep secure!)
├── db_utils.py            # Functions for database interaction
├── layouts.py             # Functions defining UI layouts
├── data/
│   ├── schema.sql         # SQL to create tables
│   └── synthetic_data.sql # SQL to insert sample data
└── requirements.txt       # List of Python dependencies
```

```
⬜ Modify DB_CONFIG with your actual PostgreSQL connection details.
⬜ check if schema.sql is similar to pgAdmin4 sql
⬜ run synthetic data.sql to populate tables
```


**How to Run:**

1.  **Setup Database:** Create the database (e.g., `access_request_db`) and run `data/schema.sql` then `data/synthetic_data.sql` using `psql` or pgAdmin 4.
2.  **Configure:** Edit `config.py` with your actual database credentials.
3.  **Install Packages:** `pip install -r requirements.txt`
4.  **Run App:** Navigate to the `dash_access_request` directory in your terminal and run `python app.py`.
5.  **Access:** Open your web browser and go to `http://127.0.0.1:8051` (or the address shown in the terminal).

---

**Application Walkthrough:**

1.  **Login Screen:**
    *   You'll see a simple login prompt asking for a User ID.
    *   Enter one of the IDs from `config.SIMULATED_USERS` (e.g., `101` for Alice, `201` for Charlie).
    *   Click "Login".

2.  **Requestor Workflow (e.g., Login as 101 - Alice):**
    *   The navbar updates to welcome Alice.
    *   The main content area shows the "Requestor Layout".
    *   You see a button "Submit New Access Request" and a table "My Access Requests".
    *   The table lists Alice's past requests (one pending, one rejected in the sample data), fetched from the database via `callbacks.load_my_requests` -> `db_utils.get_my_requests`.
    *   Click "Submit New Access Request". The button text changes to "Cancel New Request", and the request form appears below.
    *   The dropdowns for "Database Table" and "Access Role" are populated (`callbacks.populate_request_dropdowns` -> `db_utils.get_db_tables`, `db_utils.get_access_roles`).
    *   Select a table (e.g., `marketing.campaigns`) and a role (e.g., `Read`).
    *   Enter a justification (e.g., "Need to view campaign results for analysis.").
    *   Click "Submit Request".
    *   The `callbacks.handle_submit_request` function is triggered:
        *   It gets the form values and the user's info (including manager ID from simulation data).
        *   It calls `db_utils.submit_new_request` to insert the data into the `AccessRequests` table with status 'Pending' and the `approver_id` set to the requestor's manager (Charlie, ID 3).
        *   If successful, an alert message appears, the form fields are cleared, and the "My Access Requests" table refreshes to show the newly submitted request.
    *   Click "Cancel New Request" to hide the form.
    *   Click "Logout".

3.  **Approver Workflow (e.g., Login as 201 - Charlie):**
    *   Login using User ID `201`.
    *   The navbar updates to welcome Charlie.
    *   The main content area shows the "Approver Layout".
    *   You see the table "Pending Access Requests for Approval".
    *   This table lists requests assigned to Charlie (ID 3) with status 'Pending' (`callbacks.load_pending_approvals` -> `db_utils.get_pending_approvals`). You should see the requests from Alice and Bob.
    *   Each row has a "Review" button generated dynamically in the callback.
    *   Click the "Review" button for one of the requests (e.g., Alice's request for `public.customers`).
    *   The `callbacks.open_approval_modal` function is triggered (using the button ID hack):
        *   It extracts the `request_id` from the clicked button's ID.
        *   It calls `db_utils.get_request_details` to fetch detailed information.
        *   It updates the `dbc.Modal`'s title and body with the details and sets `is_open=True`, displaying the modal. The `request_id` is stored in `dcc.Store('request-id-store')`.
    *   Inside the modal:
        *   Review the details (Requester, Table, Role, Justification).
        *   Enter optional comments in the input field.
        *   Click "Approve" or "Reject".
    *   Let's say you click "Approve":
        *   The `callbacks.handle_approval_action` function triggers.
        *   It identifies 'approve-button' was clicked.
        *   It retrieves the `request_id` from the store, comments, and the approver's ID (Charlie's ID 3).
        *   It calls `db_utils.update_request_status`, setting the status to 'Approved', filling `decision_date`, `approver_comments`, and ensuring `approver_id` is correct.
        *   An alert message appears ("Request #X Approved."), the modal closes (`is_open=False`), and the "Pending Access Requests for Approval" table refreshes (the approved request disappears).
    *   If you had clicked "Reject" *without* comments, an alert would appear within the modal asking for comments. If you added comments and clicked "Reject", the status would be updated to 'Rejected'.
    *   Click "Logout".

This demonstrates the basic lifecycle of a request from submission to approval/rejection using the modular Dash application connected to the PostgreSQL database.