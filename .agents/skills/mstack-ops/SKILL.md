---
name: mstack-ops
description: Operate mstack's shared infrastructure: watcher, services, tenants, Graphify re-indexing, gateway routes and plugins. Use for maintenance or diagnosis of mstack itself; every change goes through the setup guard.
---

# mstack ops

Load `.agents/skills/mcp-stack-setup-guard/SKILL.md` first: every start, stop,
registration or config change needs the owner's approval for that step.

## Keeping projects up to date
- After changing mstack (a new skill, an ignore rule, the project skill template, a config change), run
  `mstack sync --all`. `--check` previews the changes. It updates only mstack's own files inside each project
  (skill links, `.mstack/.gitignore`, the unedited generated skill, the local `.git/info/exclude` block, config
  migrations), never team files, and commits nothing.
- A config change that existing projects must adopt goes in `integrations/stack/sync.py` `MIGRATIONS` as a new,
  higher version. Never edit a shipped migration.
- New skills: add the name to `SKILLS` in `integrations/stack/cli.py`; sync links it everywhere.
- `mstack doctor` lists pending updates under `mstack_updates`.
- Running watchers reload themselves when mstack's code changes, after syncing their project.

## Private GitHub repo
- mstack is pushed to the private repo `liyachun01/mstack` (docs/PRIVATE-REPO.md). Secrets are never committed.
  Private names (account name, emails, client names) become `{{mstack:KEY}}` placeholders in commits through the
  `mstack-private` git filter. Real values live in `.mstack/private.json`.
- Run `./mstack hydrate --check` before every push; it must report `"clean": true`.
- New private name: add it to `.mstack/private.json` (and an empty key to `.mstack/private.example.json`),
  then `git add --renormalize .`.
- New secret file: add its path (never its value) to `infra/secrets-inventory.json`.

## Working on mstack itself
Use mstack's own board and config: `.mstack/stack.json` (MST in the yyyymmdd workspace, `private: false`,
`docs_url`). One MST issue per piece of work. Write the detail in `docs/`, update affected skills, and keep the
issue short: a summary and `--doc docs/…` links (`propose`, `note` and `done` take `--doc`). Never paste long
write-ups into Linear.
From an orchestrator chat, this work goes to a worker chat; only orchestrative work and the board or ops commands
the owner asked for run there (`mstack-orchestrator` skill).

## Watcher
- `mstack board watch [--project P]` runs as a background task of an orchestrator session, with a lock per project.
- Its log is `.mstack/cache/watch.log`. To check it's alive: `ps -eo pid=,cmd= | awk '/[o]rchestrator\/cli.py watch/'`.
- Stop it by its exact PID; never by pattern-killing your own shell.

## Board store and event hub (design 011)
- `hub.store` in mstack's `.mstack/stack.json` picks where board state, private journals and the event queue live:
  `file` (default) or `postgres` (`mstack_orchestrator`). The JSON files stay the fallback either way.
- Switching to `postgres` is a setup step: with the owner's OK, `mstack events schema --apply`, then set
  `hub.store: postgres`. The first command after the switch pushes the existing files into Postgres.
- A `.pg-dirty` file next to the state file or a journal means a write missed Postgres; the next command that
  reaches Postgres pushes the file back and removes it.
- Queue: `mstack events list [--status new|sent|resolved]`; routes: `mstack orchestrators list`. The hub chat
  follows `.agents/skills/mstack-hub` and runs the only `watch --hub`.

## Services and tenants
- `mstack services status|start|stop <tool>` and `mstack tenant add --project P --tool T`.
- Stopping a shared service affects every tenant.
- **Graphify re-index:** index the non-ignored files offline (no network, read-only source, see
  docs/design/009), check for credentials first, then re-register the tenant.

## Gateway
- The live config is `infra/agentgateway/state/projects/runtime/config.yaml`.
- Back it up, edit a candidate, run `--validate-only` with `--group-add 501`, and only then apply. The gateway reloads on save.
- Project keys are stored as hashes; workers reach routes through `integrations/gateway/stdio_bridge.py`.
- Keep DNS-rebinding protection on.
- An MCP rate-limit error arrives inside an HTTP 200: check the JSON-RPC body, not the status code.

## Plugins
- `mstack plugin list|validate [--project P]`.
- A new agent or tool is a manifest under `integrations/plugins/builtin/<name>/` or the repo's own `.mstack/plugins/`.

## Tests
`for d in stack agents orchestrator plugins gateway; do python3 -m unittest discover -s integrations/$d/tests; done`.
