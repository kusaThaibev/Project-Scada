-- Schema for SCADA Monitoring Line (Machine Oriented)

-- 1. Machines table (Each tag belongs to a machine/station)
CREATE TABLE IF NOT EXISTS machines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_name TEXT NOT NULL UNIQUE,
    description TEXT
);

-- 2. Configuration table for Tags
CREATE TABLE IF NOT EXISTS tag_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id INTEGER,                   -- Linked to machines table
    tag_name TEXT NOT NULL,               
    opc_address TEXT NOT NULL UNIQUE,     
    is_active BOOLEAN DEFAULT 1,          
    
    -- Performance & Filtering
    deadband REAL DEFAULT 0,              
    update_interval INTEGER DEFAULT 1,    
    
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (machine_id) REFERENCES machines(id)
);

-- 3. Snapshot table
CREATE TABLE IF NOT EXISTS tag_latest_snapshot (
    tag_id INTEGER PRIMARY KEY,
    last_value TEXT,
    last_status TEXT,
    last_update TIMESTAMP,
    FOREIGN KEY (tag_id) REFERENCES tag_config(id)
);

-- 4. History table
CREATE TABLE IF NOT EXISTS raw_data_pool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_id INTEGER,
    tag_value TEXT,
    status_code TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tag_id) REFERENCES tag_config(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_raw_data_timestamp ON raw_data_pool(timestamp);
CREATE INDEX IF NOT EXISTS idx_raw_data_tag_id ON raw_data_pool(tag_id);
CREATE INDEX IF NOT EXISTS idx_tag_config_active ON tag_config(is_active);
