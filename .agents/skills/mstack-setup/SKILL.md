---
name: mstack-setup
description: Bring a repository into mstack: local (gitignored) setup, app codes, team tools versus mstack tools, and Linear links from the owner's key file. Use when the owner asks to add mstack to a repo or link a repo or app to Linear.
---

# mstack setup

All commands are `/home/developer/workspace/mstack/mstack …`. Load the setup guard
(`.agents/skills/mcp-stack-setup-guard/SKILL.md` in the mstack repo) before any service,
tenant or MCP change. Never edit the team's files (`.gitignore`, `AGENTS.md`, `.mcp.json`,
`.claude/settings.json`).

1. **Init, local by default:** `mstack init <repo> --name <slug> --preset solo --local`.
   - Everything goes under `.mstack/` and is hidden through `.git/info/exclude`.
   - A protected repo ({{mstack:CLIENT_REPO}}) needs `--allow-protected`, and only when the owner said so. Its Supabase containers, networks and volumes are never touched.
2. **Skills:** `mstack skills --project <repo>` links these skills into the repo, locally.
3. **Board:** in `.mstack/stack.json`, set
   `taskboard: {table, backend: "linear", workers: ["claude-desktop", "codex-desktop"], auto: true}`.
   For monorepos, add `apps: {CODE: {path: "apps/<name>"}}`.
4. **Linear links,** one per repo or per app. Use only the owner's key file:
   `mstack board link --project <repo> --entry <N> --team <KEY> [--app CODE]`.
   - It verifies the key live and copies it into that repo's `.mstack/secrets/` (0600).
   - Never create teams, labels or states in the owner's workspaces.
5. **Tools:**
   - **Team tools** (the repo's own `.mcp.json`: Headroom, Serena, Graphify) → `tools.<name>.source: "project"`. mstack containers don't join.
   - **mstack tools,** for repos without their own → `mstack tenant add --tool headroom|graphify` (Graphify needs an offline index), then `joints`.
6. **Register and check:** `mstack board table --project <repo>`, then `mstack doctor --project <repo>` until it reports ready.
7. **Report** what changed (git status should show nothing new) and what is waiting on the owner.

Why it works this way: docs/design/010-LINEAR-SESSIONS.md, docs/MSTACK-CONFIG.md.
