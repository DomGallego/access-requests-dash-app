-- 02_synthetic_data.sql

-- Ensure AccessRoles are populated if not done in schema script
-- INSERT INTO AccessRoles (role_name, description) VALUES
-- ('Read', 'Permission to SELECT data from the table.'),
-- ('Write', 'Permission to INSERT, UPDATE, DELETE data in the table.'),
-- ('Read-Write', 'Combines Read and Write permissions.')
-- ON CONFLICT (role_name) DO NOTHING;


-- Populate DatabaseTables
INSERT INTO DatabaseTables (schema_name, table_name, description) VALUES
('public', 'customers', 'Stores customer profile information.'),
('public', 'transactions', 'Logs all financial transactions.'),
('public', 'accounts', 'Manages user account balances and types.'),
('finance_data', 'gl_entries', 'General ledger entries for accounting.'),
('marketing_data', 'campaign_results', 'Results from marketing campaigns.'),
('internal', 'employee_performance', 'HR data on employee performance reviews (Highly Sensitive).')
ON CONFLICT (schema_name, table_name) DO NOTHING;


-- Populate Employees (Managers first, then Requestors)
-- Managers (Approvers)
INSERT INTO Employees (first_name, last_name, email, department, is_manager) VALUES
('Maria', 'Santos', 'maria.santos@example.com', 'Finance', TRUE),        -- employee_id will be 1
('Jose', 'Reyes', 'jose.reyes@example.com', 'Operations', TRUE),       -- employee_id will be 2
('Ana', 'Garcia', 'ana.garcia@example.com', 'Marketing', TRUE),        -- employee_id will be 3
('Carlos', 'Cruz', 'carlos.cruz@example.com', 'IT', TRUE),            -- employee_id will be 4
('Sofia', 'Bautista', 'sofia.bautista@example.com', 'HR', TRUE);        -- employee_id will be 5

-- Requestors (assign managers using their assumed IDs)
INSERT INTO Employees (first_name, last_name, email, department, manager_id, is_manager) VALUES
('Juan', 'Dela Cruz', 'juan.delacruz@example.com', 'Finance', 1, FALSE),      -- employee_id will be 6
('Pedro', 'Ramos', 'pedro.ramos@example.com', 'Finance', 1, FALSE),         -- employee_id will be 7
('Isabella', 'Villanueva', 'isabella.villanueva@example.com', 'Operations', 2, FALSE), -- employee_id will be 8
('Miguel', 'Fernandez', 'miguel.fernandez@example.com', 'Operations', 2, FALSE),  -- employee_id will be 9
('Bea', 'Torres', 'bea.torres@example.com', 'Marketing', 3, FALSE),        -- employee_id will be 10
('Luis', 'Gonzales', 'luis.gonzales@example.com', 'Marketing', 3, FALSE),     -- employee_id will be 11
('Katrina', 'Flores', 'katrina.flores@example.com', 'IT', 4, FALSE),       -- employee_id will be 12
('Andres', 'Mercado', 'andres.mercado@example.com', 'IT', 4, FALSE),       -- employee_id will be 13
('Bianca', 'Lim', 'bianca.lim@example.com', 'HR', 5, FALSE),             -- employee_id will be 14
('Rafael', 'Chua', 'rafael.chua@example.com', 'HR', 5, FALSE);            -- employee_id will be 15


-- Populate UserCredentials (linking to existing employees by their assumed IDs)
-- Passwords are VERY insecurely stored. FOR MVP/DEMO ONLY.
INSERT INTO UserCredentials (employee_id, username, password_text) VALUES
(1, 'maria.santos@example.com', 'PassMaria123!'),
(2, 'jose.reyes@example.com', 'PassJose456@'),
(3, 'ana.garcia@example.com', 'PassAna789#'),
(4, 'carlos.cruz@example.com', 'PassCarlos101$'),
(5, 'sofia.bautista@example.com', 'PassSofia202%'),
(6, 'juan.delacruz@example.com', 'PassJuan303^'),
(7, 'pedro.ramos@example.com', 'PassPedro404&'),
(8, 'isabella.villanueva@example.com', 'PassIsabella505*'),
(9, 'miguel.fernandez@example.com', 'PassMiguel606('),
(10, 'bea.torres@example.com', 'PassBea707)'),
(11, 'luis.gonzales@example.com', 'PassLuis808_'),
(12, 'katrina.flores@example.com', 'PassKatrina909+'),
(13, 'andres.mercado@example.com', 'PassAndres010='),
(14, 'bianca.lim@example.com', 'PassBianca111~'),
(15, 'rafael.chua@example.com', 'PassRafael212`')
ON CONFLICT DO NOTHING;


-- Populate AccessRequests (using assumed IDs for employees, tables, and roles)
-- Assumed IDs:
-- Employees: Managers 1-5, Requestors 6-15
-- DatabaseTables: customers=1, transactions=2, accounts=3, gl_entries=4, campaign_results=5, employee_performance=6
-- AccessRoles: Read=1, Write=2, Read-Write=3

-- Pending Requests
INSERT INTO AccessRequests (requester_id, table_id, requested_role_id, justification, request_date) VALUES
(6, 1, 1, 'Need to view customer data for Q3 financial report.', NOW() - INTERVAL '2 days'), -- Juan requests Read on customers
(8, 2, 1, 'Daily transaction monitoring for operational integrity.', NOW() - INTERVAL '1 day'), -- Isabella requests Read on transactions
(10, 5, 3, 'Need to update and analyze marketing campaign performance data.', NOW() - INTERVAL '3 hours'); -- Bea requests Read-Write on campaign_results

-- Approved Requests
INSERT INTO AccessRequests (requester_id, table_id, requested_role_id, justification, request_date, status, approver_id, decision_date, approver_comments) VALUES
(7, 3, 1, 'Need read access to accounts table for monthly reconciliation.', NOW() - INTERVAL '5 days', 'Approved', 1, NOW() - INTERVAL '4 days', 'Approved. Access granted for reconciliation tasks.'), -- Pedro requests Read on accounts, approved by Maria
(9, 4, 1, 'Required for generating operational efficiency reports on GL entries.', NOW() - INTERVAL '7 days', 'Approved', 2, NOW() - INTERVAL '6 days', 'Approved for reporting purposes.'), -- Miguel requests Read on gl_entries, approved by Jose
(12, 1, 3, 'Full access to customer table needed for IT support and data correction tasks.', NOW() - INTERVAL '3 days', 'Approved', 4, NOW() - INTERVAL '2 days', 'Approved. Handle customer data with care.'); -- Katrina requests Read-Write on customers, approved by Carlos

-- Rejected Requests
INSERT INTO AccessRequests (requester_id, table_id, requested_role_id, justification, request_date, status, approver_id, decision_date, approver_comments) VALUES
(11, 6, 3, 'Want to see all employee performance data.', NOW() - INTERVAL '4 days', 'Rejected', 5, NOW() - INTERVAL '3 days', 'Rejected. Access to highly sensitive HR data requires stronger justification and is role-restricted. Please specify exact needs.'), -- Luis requests Read-Write on employee_performance, rejected by Sofia
(14, 2, 2, 'Need to perform bulk updates on transaction records for testing.', NOW() - INTERVAL '6 days', 'Rejected', 2, NOW() - INTERVAL '5 days', 'Rejected. Write access to transactions table is highly restricted. Please use staging environment for testing.'); -- Bianca requests Write on transactions, rejected by Jose

COMMIT;