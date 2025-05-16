-- 01_schema_setup.sql

-- Drop tables in reverse order of dependency to avoid FK constraint errors
DROP TABLE IF EXISTS UserCredentials CASCADE;
DROP TABLE IF EXISTS AccessRequests CASCADE;
DROP TABLE IF EXISTS AccessRoles CASCADE;
DROP TABLE IF EXISTS DatabaseTables CASCADE;
DROP TABLE IF EXISTS Employees CASCADE;

-- Table: Employees
CREATE TABLE Employees (
    employee_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    department VARCHAR(50),
    manager_id INT NULL,
    is_manager BOOLEAN DEFAULT FALSE,
    CONSTRAINT fk_manager
        FOREIGN KEY(manager_id)
        REFERENCES Employees(employee_id)
        ON DELETE SET NULL -- If a manager is deleted, employees under them are not deleted, but manager_id becomes NULL
);
COMMENT ON TABLE Employees IS 'Stores information about company employees.';
COMMENT ON COLUMN Employees.manager_id IS 'Self-referencing FK to the employee_id of the manager.';
COMMENT ON COLUMN Employees.is_manager IS 'Flag indicating if the employee has approval capabilities.';

-- Table: UserCredentials
CREATE TABLE UserCredentials (
    credential_id SERIAL PRIMARY KEY,
    employee_id INT UNIQUE NOT NULL, -- Ensures one credential set per employee
    username VARCHAR(100) UNIQUE NOT NULL, -- Typically the email
    password_text VARCHAR(255) NOT NULL, -- Storing password in plain text (NOT FOR PRODUCTION)
    CONSTRAINT fk_employee_credentials
        FOREIGN KEY(employee_id)
        REFERENCES Employees(employee_id)
        ON DELETE CASCADE -- If an employee is deleted, their credentials are also deleted
);
COMMENT ON TABLE UserCredentials IS 'Stores login credentials for employees. Password stored in plain text for MVP purposes ONLY.';
COMMENT ON COLUMN UserCredentials.username IS 'Username for login, typically the employee''s email.';
COMMENT ON COLUMN UserCredentials.password_text IS 'Plain text password (DEVELOPMENT/MVP ONLY).';


-- Table: DatabaseTables
CREATE TABLE DatabaseTables (
    table_id SERIAL PRIMARY KEY,
    schema_name VARCHAR(63) NOT NULL DEFAULT 'public', -- PostgreSQL default schema name max length
    table_name VARCHAR(63) NOT NULL,
    description TEXT,
    UNIQUE (schema_name, table_name) -- Ensure table uniqueness within a schema
);
COMMENT ON TABLE DatabaseTables IS 'Represents specific database tables to which access can be requested.';
COMMENT ON COLUMN DatabaseTables.schema_name IS 'Name of the database schema (e.g., ''public'').';
COMMENT ON COLUMN DatabaseTables.table_name IS 'Name of the database table.';

-- Table: AccessRoles
CREATE TABLE AccessRoles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(20) UNIQUE NOT NULL CHECK (role_name IN ('Read', 'Write', 'Read-Write')),
    description TEXT
);
COMMENT ON TABLE AccessRoles IS 'Defines the types of access levels that can be requested (e.g., Read, Write).';
COMMENT ON COLUMN AccessRoles.role_name IS 'Name of the access role (e.g., ''Read'', ''Write'', ''Read-Write'').';

-- Table: AccessRequests
CREATE TABLE AccessRequests (
    request_id SERIAL PRIMARY KEY,
    requester_id INT NOT NULL,
    table_id INT NOT NULL,
    requested_role_id INT NOT NULL,
    justification TEXT NOT NULL,
    request_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(10) NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Approved', 'Rejected')),
    approver_id INT NULL, -- Filled when approved/rejected
    decision_date TIMESTAMP NULL, -- When the decision was made
    approver_comments TEXT NULL, -- Comments from the approver

    CONSTRAINT fk_requester
        FOREIGN KEY(requester_id)
        REFERENCES Employees(employee_id)
        ON DELETE CASCADE, -- If an employee is deleted, their requests might be removed or archived differently depending on policy. Cascade for simplicity here.

    CONSTRAINT fk_table
        FOREIGN KEY(table_id)
        REFERENCES DatabaseTables(table_id)
        ON DELETE RESTRICT, -- Prevent deleting a table if requests exist for it

    CONSTRAINT fk_requested_role
        FOREIGN KEY(requested_role_id)
        REFERENCES AccessRoles(role_id)
        ON DELETE RESTRICT, -- Prevent deleting a role if requests use it

    CONSTRAINT fk_approver
        FOREIGN KEY(approver_id)
        REFERENCES Employees(employee_id)
        ON DELETE SET NULL -- If an approver leaves, keep the record but nullify the approver link
);
COMMENT ON TABLE AccessRequests IS 'Captures details of each database access request, its status, and approval information.';
COMMENT ON COLUMN AccessRequests.requester_id IS 'FK to Employees: The employee who made the request.';
COMMENT ON COLUMN AccessRequests.table_id IS 'FK to DatabaseTables: The table access is requested for.';
COMMENT ON COLUMN AccessRequests.requested_role_id IS 'FK to AccessRoles: The type of access requested.';
COMMENT ON COLUMN AccessRequests.status IS 'Current status of the request (Pending, Approved, Rejected).';
COMMENT ON COLUMN AccessRequests.approver_id IS 'FK to Employees: The manager who approved/rejected the request.';

-- Indexing for performance on frequently queried columns
CREATE INDEX idx_accessrequests_requester_id ON AccessRequests(requester_id);
CREATE INDEX idx_accessrequests_approver_id ON AccessRequests(approver_id);
CREATE INDEX idx_accessrequests_status ON AccessRequests(status);
CREATE INDEX idx_employees_email ON Employees(email);
CREATE INDEX idx_usercredentials_username ON UserCredentials(username);

-- Initial roles
INSERT INTO AccessRoles (role_name, description) VALUES
('Read', 'Permission to SELECT data from the table.'),
('Write', 'Permission to INSERT, UPDATE, DELETE data in the table.'),
('Read-Write', 'Combines Read and Write permissions.');

COMMIT;