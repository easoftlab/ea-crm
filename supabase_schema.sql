-- EA CRM Supabase PostgreSQL Schema
-- Run this in your Supabase SQL Editor

-- Enable Row Level Security (RLS)
ALTER TABLE IF EXISTS users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS tasks ENABLE ROW LEVEL SECURITY;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    email TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Leads table
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    company TEXT,
    status TEXT DEFAULT 'new',
    source TEXT,
    notes TEXT,
    assigned_to TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
    due_date DATE,
    assigned_to TEXT,
    lead_id INTEGER REFERENCES leads(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default admin user
INSERT INTO users (username, password, role, email) 
VALUES ('admin', 'admin123', 'admin', 'admin@eacrm.com')
ON CONFLICT (username) DO NOTHING;

-- Insert sample leads
INSERT INTO leads (name, email, phone, company, status, source, notes, assigned_to) VALUES 
('John Doe', 'john@example.com', '+1234567890', 'Tech Corp', 'new', 'website', 'Interested in CRM solution', 'admin'),
('Jane Smith', 'jane@example.com', '+0987654321', 'Marketing Inc', 'contacted', 'referral', 'Follow up needed for demo', 'admin'),
('Mike Johnson', 'mike@startup.com', '+1122334455', 'StartupXYZ', 'qualified', 'cold_call', 'Ready for proposal', 'admin')
ON CONFLICT DO NOTHING;

-- Insert sample tasks
INSERT INTO tasks (title, description, status, priority, due_date, assigned_to, lead_id) VALUES 
('Follow up with John Doe', 'Call about CRM demo and pricing', 'pending', 'high', '2025-08-10', 'admin', 1),
('Update website content', 'Add new features page and pricing', 'in_progress', 'medium', '2025-08-15', 'admin', NULL),
('Send proposal to Jane Smith', 'Prepare custom proposal for Marketing Inc', 'pending', 'high', '2025-08-12', 'admin', 2)
ON CONFLICT DO NOTHING;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_assigned_to ON leads(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_leads_updated_at BEFORE UPDATE ON leads FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security Policies
-- Users can read their own data and admin can read all
CREATE POLICY "Users can view own data" ON users FOR SELECT USING (auth.uid()::text = username OR role = 'admin');
CREATE POLICY "Admin can manage users" ON users FOR ALL USING (role = 'admin');

-- Leads policies
CREATE POLICY "Users can view leads" ON leads FOR SELECT USING (true);
CREATE POLICY "Users can insert leads" ON leads FOR INSERT WITH CHECK (true);
CREATE POLICY "Users can update leads" ON leads FOR UPDATE USING (true);
CREATE POLICY "Users can delete leads" ON leads FOR DELETE USING (true);

-- Tasks policies
CREATE POLICY "Users can view tasks" ON tasks FOR SELECT USING (true);
CREATE POLICY "Users can insert tasks" ON tasks FOR INSERT WITH CHECK (true);
CREATE POLICY "Users can update tasks" ON tasks FOR UPDATE USING (true);
CREATE POLICY "Users can delete tasks" ON tasks FOR DELETE USING (true);

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated; 