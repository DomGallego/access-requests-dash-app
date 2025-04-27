-- data/synthetic_data.sql

-- Insert Roles (Assuming schema.sql already ran)
INSERT INTO AccessRoles (role_name, description) VALUES
('Read', 'Permission to SELECT data from the table.'),
('Write', 'Permission to INSERT, UPDATE, DELETE data in the table.'),
('Read-Write', 'Combines Read and Write permissions.')
ON CONFLICT (role_name) DO NOTHING; -- Avoid errors if run multiple times

-- Insert Employees
INSERT INTO Employees (employee_id, first_name, last_name, email, department, manager_id, is_manager) VALUES
(1, 'Alice', 'Wonder', 'alice.w@example.com', 'Marketing', 3, FALSE),
(2, 'Bob', 'Builder', 'bob.b@example.com', 'Sales', 3, FALSE),
(3, 'Charlie', 'Chaplin', 'charlie.c@example.com', 'Management', NULL, TRUE),
(4, 'Diana', 'Prince', 'diana.p@example.com', 'Finance', 5, FALSE),
(5, 'Edward', 'Scissorhands', 'edward.s@example.com', 'Management', NULL, TRUE)
ON CONFLICT (email) DO NOTHING;
-- Update sequences if needed after manual ID insertion
SELECT setval(pg_get_serial_sequence('employees', 'employee_id'), coalesce(max(employee_id), 1)) FROM employees;


-- Insert Database Tables
INSERT INTO DatabaseTables (schema_name, table_name, description) VALUES
('public', 'customers', 'Contains customer profile information.'),
('public', 'orders', 'Contains customer order history.'),
('finance', 'transactions', 'Detailed financial transaction records.'),
('marketing', 'campaigns', 'Details about marketing campaigns.'),
('sales', 'leads', 'Information about potential sales leads.')
ON CONFLICT (schema_name, table_name) DO NOTHING;
SELECT setval(pg_get_serial_sequence('databasetables', 'table_id'), coalesce(max(table_id), 1)) FROM databasetables;


-- Insert Sample Access Requests
-- Request 1: Alice needs read access to customers (Pending for Charlie)
INSERT INTO AccessRequests (requester_id, table_id, requested_role_id, justification, status, approver_id)
SELECT 1, t.table_id, r.role_id, 'Need to analyze customer demographics for Marketing report Q3.', 'Pending', 3
FROM DatabaseTables t, AccessRoles r
WHERE t.schema_name = 'public' AND t.table_name = 'customers' AND r.role_name = 'Read';

-- Request 2: Bob needs read-write access to leads (Pending for Charlie)
INSERT INTO AccessRequests (requester_id, table_id, requested_role_id, justification, status, approver_id)
SELECT 2, t.table_id, r.role_id, 'Need to update lead statuses and contact info in Sales.', 'Pending', 3
FROM DatabaseTables t, AccessRoles r
WHERE t.schema_name = 'sales' AND t.table_name = 'leads' AND r.role_name = 'Read-Write';

-- Request 3: Diana needs read access to transactions (Approved by Edward)
INSERT INTO AccessRequests (requester_id, table_id, requested_role_id, justification, status, approver_id, decision_date, approver_comments)
SELECT 4, t.table_id, r.role_id, 'Required for monthly financial reconciliation.', 'Approved', 5, CURRENT_TIMESTAMP - INTERVAL '1 day', 'Approved for standard reporting.'
FROM DatabaseTables t, AccessRoles r
WHERE t.schema_name = 'finance' AND t.table_name = 'transactions' AND r.role_name = 'Read';

-- Request 4: Alice needs read access to orders (Rejected by Charlie)
INSERT INTO AccessRequests (requester_id, table_id, requested_role_id, justification, status, approver_id, decision_date, approver_comments)
SELECT 1, t.table_id, r.role_id, 'Want to see order patterns.', 'Rejected', 3, CURRENT_TIMESTAMP - INTERVAL '2 hours', 'Justification too vague. Please provide specific project need.'
FROM DatabaseTables t, AccessRoles r
WHERE t.schema_name = 'public' AND t.table_name = 'orders' AND r.role_name = 'Read';

-- Request 5: Diana needs write access to transactions (Pending for Edward)
INSERT INTO AccessRequests (requester_id, table_id, requested_role_id, justification, status, approver_id)
SELECT 4, t.table_id, r.role_id, 'Need to correct transaction entry #12345.', 'Pending', 5
FROM DatabaseTables t, AccessRoles r
WHERE t.schema_name = 'finance' AND t.table_name = 'transactions' AND r.role_name = 'Write';

SELECT setval(pg_get_serial_sequence('accessrequests', 'request_id'), coalesce(max(request_id), 1)) FROM accessrequests;