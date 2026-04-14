-- CoreDump Dashboard Schema - Enhanced for Crash Simulator

CREATE TABLE IF NOT EXISTS crashes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    unix_timestamp INTEGER NOT NULL,
    type INTEGER NOT NULL,
    file TEXT,
    line INTEGER,
    function TEXT,
    process_id INTEGER,
    thread_id INTEGER,
    stack_depth INTEGER,
    cpu_usage REAL,
    memory_used_kb INTEGER,
    memory_total_kb INTEGER,
    probable_cause TEXT,
    severity TEXT,
    confidence_score INTEGER,
    raw_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- New fields for crash_simulator compatibility
    category_name TEXT,
    seed INTEGER,
    description TEXT,
    call_chain_depth INTEGER,
    exception_code INTEGER,
    intensity INTEGER,
    recursion_depth INTEGER,
    memory_size INTEGER,
    random_mode BOOLEAN,
    generate_minidump BOOLEAN
);

CREATE TABLE IF NOT EXISTS call_stack (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crash_id INTEGER NOT NULL,
    frame_index INTEGER NOT NULL,
    address TEXT NOT NULL,
    decoded_function TEXT,
    decoded_file TEXT,
    decoded_line INTEGER,
    FOREIGN KEY (crash_id) REFERENCES crashes(id)
);

CREATE INDEX IF NOT EXISTS idx_timestamp ON crashes(timestamp);
CREATE INDEX IF NOT EXISTS idx_severity ON crashes(severity);
CREATE INDEX IF NOT EXISTS idx_type ON crashes(type);
CREATE INDEX IF NOT EXISTS idx_category_name ON crashes(category_name);
CREATE INDEX IF NOT EXISTS idx_unix_timestamp ON crashes(unix_timestamp);