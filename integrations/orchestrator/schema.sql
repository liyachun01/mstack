-- mstack orchestrator store in Postgres mstack_orchestrator (design 011, phase 1).
-- Idempotent. Applying it is an owner-approved setup step: `mstack events schema --apply`.
-- Run as the database owner role mstack_orchestrator; mstack_viewer (WhoDB) only reads.
CREATE SCHEMA IF NOT EXISTS orchestrator;

-- Board state: one row per top-level key of the old state file
-- (tables, runs, related, task_tables, task_repos, attention_seen, orchestrators, last_* poll timers).
CREATE TABLE IF NOT EXISTS orchestrator.board_state (
  key        text PRIMARY KEY,
  value      jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Private-board journals: the orchestrator's and the owner's comments that never go to Linear.
CREATE TABLE IF NOT EXISTS orchestrator.journal (
  id         text PRIMARY KEY,
  project    text NOT NULL,              -- the project's path
  issue      text NOT NULL,              -- Linear issue id
  body       text NOT NULL,
  created_at timestamptz NOT NULL,
  reactions  jsonb NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS journal_project_issue ON orchestrator.journal (project, issue, created_at);

-- Event queue: new -> sent -> resolved. Resolved only by the receiving orchestrator.
CREATE TABLE IF NOT EXISTS orchestrator.queue (
  id          bigserial PRIMARY KEY,
  created_at  timestamptz NOT NULL DEFAULT now(),
  board       text NOT NULL,             -- table name (e.g. {{mstack:CLIENT_REPO}})
  scope       text NOT NULL DEFAULT '',  -- orchestrator scope; '' = the whole board
  kind        text NOT NULL,             -- plan, replan, forward, stop, handoff, resume, verdict, merged, new_issue, mention
  task        text,
  issue       text,
  dedupe      text UNIQUE,               -- repeats of the same signal return the existing row
  payload     jsonb NOT NULL DEFAULT '{}',
  status      text NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'sent', 'resolved')),
  session     text,                      -- recipient when last sent
  sends       integer NOT NULL DEFAULT 0,
  sent_at     timestamptz,
  resolved_at timestamptz,
  resolved_by text,
  note        text
);
CREATE INDEX IF NOT EXISTS queue_open ON orchestrator.queue (status, created_at) WHERE status <> 'resolved';

-- The local Linear issue table (`mstack board mirror`); already present on this installation.
CREATE TABLE IF NOT EXISTS orchestrator.issues (
  board text NOT NULL, identifier text NOT NULL, linear_id text, team text, app text, title text, state text,
  state_type text, parent text, focus boolean, scopes text, managed boolean, agent_phase text, url text,
  updated_at timestamptz, synced_at timestamptz, present boolean,
  PRIMARY KEY (board, identifier)
);

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mstack_viewer') THEN
    GRANT USAGE ON SCHEMA orchestrator TO mstack_viewer;
    GRANT SELECT ON orchestrator.board_state, orchestrator.journal, orchestrator.queue TO mstack_viewer;
  END IF;
END $$;
