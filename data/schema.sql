-- data/schema.sql

DROP TABLE IF EXISTS AccessRequests CASCADE;
DROP TABLE IF EXISTS AccessRoles CASCADE;
DROP TABLE IF EXISTS DatabaseTables CASCADE;
DROP TABLE IF EXISTS Employees CASCADE;

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
        ON DELETE SET NULL
);

CREATE TABLE DatabaseTables (
    table_id SERIAL PRIMARY KEY,
    schema_name VARCHAR(63) NOT NULL,
    table_name VARCHAR(63) NOT NULL,
    description TEXT,
    UNIQUE (schema_name, table_name)
);

CREATE TABLE AccessRoles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(20) UNIQUE NOT NULL CHECK (role_name IN ('Read', 'Write', 'Read-Write')),
    description TEXT
);

CREATE TABLE AccessRequests (
    request_id SERIAL PRIMARY KEY,
    requester_id INT NOT NULL,
    table_id INT NOT NULL,
    requested_role_id INT NOT NULL,
    justification TEXT NOT NULL,
    request_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(10) NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Approved', 'Rejected')),
    approver_id INT NULL,
    decision_date TIMESTAMP NULL,
    approver_comments TEXT NULL,

    CONSTRAINT fk_requester
        FOREIGN KEY(requester_id)
        REFERENCES Employees(employee_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_table
        FOREIGN KEY(table_id)
        REFERENCES DatabaseTables(table_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_requested_role
        FOREIGN KEY(requested_role_id)
        REFERENCES AccessRoles(role_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_approver
        FOREIGN KEY(approver_id)
        REFERENCES Employees(employee_id)
        ON DELETE SET NULL
);

-- Add index for faster lookup of pending requests for a manager
CREATE INDEX idx_pending_requests ON AccessRequests (approver_id, status) WHERE status = 'Pending';