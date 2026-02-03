CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  description TEXT NOT NULL,
  category TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  claimed_by TEXT,
  claimed_at INTEGER,
  completed_at INTEGER,
  result TEXT,
  error TEXT
);

CREATE TABLE IF NOT EXISTS heartbeats (
  agent_id TEXT PRIMARY KEY,
  last_heartbeat INTEGER NOT NULL,
  current_task_id TEXT
);

CREATE TABLE IF NOT EXISTS swarm_session (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  session_id TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  agent_count INTEGER NOT NULL,
  started_at INTEGER NOT NULL,
  completed_at INTEGER
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category);
