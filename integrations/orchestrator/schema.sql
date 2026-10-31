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
  kind        text NOT NULL,             -- plan, replan, forward, stop, handoff, resume, verdict, merged, new_issue, mention, status_lag, review_reply, catch_up
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

-- Mailbox and conductor (design 016 §2, 017 M1; MST-67). Additive: no existing row is rewritten.
-- A NULL recipient means the old route: orch:<board>[/<scope>], derived in code.
ALTER TABLE orchestrator.queue ADD COLUMN IF NOT EXISTS recipient text;   -- orch:<board>[/<scope>], worker:<ISSUE>, owner, dock
ALTER TABLE orchestrator.queue ADD COLUMN IF NOT EXISTS sender text;      -- linear, owner, conductor, or an agent address
ALTER TABLE orchestrator.queue ADD COLUMN IF NOT EXISTS turn text;        -- the conductor turn that holds it (status sent)
ALTER TABLE orchestrator.queue ADD COLUMN IF NOT EXISTS attempts integer NOT NULL DEFAULT 0;
ALTER TABLE orchestrator.queue DROP CONSTRAINT IF EXISTS queue_status_check;
ALTER TABLE orchestrator.queue ADD CONSTRAINT queue_status_check CHECK (status IN ('new', 'sent', 'held', 'resolved'));
CREATE INDEX IF NOT EXISTS queue_recipient_open ON orchestrator.queue (recipient, status, id) WHERE status <> 'resolved';

-- Conductor-hosted agents: runtime state only; intent stays in each project's .mstack/stack.json.
CREATE TABLE IF NOT EXISTS orchestrator.agents (
  address       text PRIMARY KEY,           -- orch:mstack, orch:{{mstack:CLIENT_REPO}}/customer-api, worker:MST-70
  role          text NOT NULL,              -- orchestrator, sub-orchestrator, worker, dock
  harness       text NOT NULL,              -- {{mstack:CLIENT_C_FOLDER}}, dsh, claude-desktop
  session       text,                       -- native session: {{mstack:CLIENT_C_FOLDER}}:<team>/<channel>, dsh:<id>, local_…
  parent        text,
  state         text NOT NULL DEFAULT 'idle' CHECK (state IN ('idle', 'running', 'paused', 'archived')),
  mode          text NOT NULL DEFAULT 'shadow' CHECK (mode IN ('shadow', 'live')),
  model         text,
  playbook_hash text,                       -- the PLAYBOOK.md the agent last received
  cursor        jsonb NOT NULL DEFAULT '{}',-- harness read position (e.g. the last chat sequence seen)
  day           date,
  turns_day     integer NOT NULL DEFAULT 0,
  failures      integer NOT NULL DEFAULT 0, -- consecutive failed turns; 3 pauses the agent
  last_wake     timestamptz,
  last_result   text,
  updated_at    timestamptz NOT NULL DEFAULT now()
);

-- One row per conductor turn (a batch sent to one agent).
CREATE TABLE IF NOT EXISTS orchestrator.turns (
  id          text PRIMARY KEY,
  address     text NOT NULL,
  events      bigint[] NOT NULL DEFAULT '{}',
  attempt     integer NOT NULL DEFAULT 1,
  status      text NOT NULL CHECK (status IN ('running', 'done', 'no_actions', 'failed')),
  sent_ref    text,                         -- the harness message id/sequence of the batch
  reply       text,                         -- the agent's message holding the actions block
  error       text,
  started_at  timestamptz NOT NULL DEFAULT now(),
  ended_at    timestamptz
);
CREATE INDEX IF NOT EXISTS turns_address ON orchestrator.turns (address, started_at);

-- Execute-once log: an action's key is recorded before it runs, so a retried turn never runs it twice.
CREATE TABLE IF NOT EXISTS orchestrator.actions (
  key        text PRIMARY KEY,              -- sha256(address, event ids, index, action)
  turn       text,
  address    text NOT NULL,
  action     jsonb NOT NULL,
  status     text NOT NULL CHECK (status IN ('running', 'done', 'failed', 'refused', 'shadow')),
  result     jsonb,
  reason     text,
  created_at timestamptz NOT NULL DEFAULT now(),
  done_at    timestamptz
);
CREATE INDEX IF NOT EXISTS actions_turn ON orchestrator.actions (turn);

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mstack_viewer') THEN
    GRANT USAGE ON SCHEMA orchestrator TO mstack_viewer;
    GRANT SELECT ON orchestrator.board_state, orchestrator.journal, orchestrator.queue, orchestrator.agents,
                    orchestrator.turns, orchestrator.actions TO mstack_viewer;
  END IF;
END $$;
