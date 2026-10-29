---
name: mstack-ops
description: Operate mstack's shared infrastructure: watcher, services, tenants, Graphify re-indexing, gateway routes and plugins. Use for maintenance or diagnosis of mstack itself; every change goes through the setup guard.
---

# mstack ops

Load `.agents/skills/mcp-stack-setup-guard/SKILL.md` first: every start, stop,
registration or config change needs the owner's approval for that step.

## Watcher
- `mstack board watch [--project P]` runs as a background task of an orchestrator session, with a lock per project.
- Its log is `.mstack/cache/watch.log`. To check it's alive: `ps -eo pid=,cmd= | awk '/[o]rchestrator\/cli.py watch/'`.
- Stop it by its exact PID; never by pattern-killing your own shell.

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
