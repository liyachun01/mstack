---
name: mstack-models
description: Pick the model and harness for a piece of work (official Claude, DeepSeek through Magpie, DeepSeek Harness, OpenCode, local Llama) and route an mstack issue to it. Use when the owner says work should run on DeepSeek or a local model, or asks which harness to use.
---

# mstack models and harnesses

The harness (the app or CLI that runs the agent) is a separate choice from the model it calls.
Choose per task, record the choice on the issue, and never switch the owner's global login or settings.

## What exists (verify before relying on it)
| Route | How | State |
|---|---|---|
| Claude Desktop, official login | default app profile (`~/Library/Application Support/Claude`) | in use |
| Claude Desktop → Magpie → DeepSeek | third-party profile in `Claude-3p/configLibrary`, gateway `127.0.0.1:3425` | profile kept, Magpie running; see `infra/magpie/README.md` |
| DeepSeek Harness (`dsh`) headless | `dsh` worker runner (`integrations/plugins/builtin/dsh`) → `integrations/agents/dsh_launch.py` (qualified settings, `--dry-run`, `--check`) | qualified (MST-56) and wired to the real dsh (MST-62); **no real issue run yet**: the first one waits for the owner's 👍 on MST-62. Lower priority since 2026-10-30 (orchestrators move to a dedicated host app, MST-66). The retained web profile is never used for workers |
| OpenCode | `integrations/plugins/builtin/opencode` runner (`opencode run`) | runner written; binary not installed |
| Llama.app (local) | `http://127.0.0.1:9931/v1` on the Mac | app installed; no model weights yet |

Check that a route is up before using it, read-only:
`macctl run /Applications/magpie.app/Contents/MacOS/magpie claude-desktop` (current Magpie binding),
`command -v dsh opencode`, and `mstack plugin list` (runners and whether each is available).

## Choosing
- **Code that changes the repo, long multi-file work, reviews:** official Claude (Desktop session or worker).
- **Bulk or cheap work where the owner asked for DeepSeek** (drafting, summarising, data wrangling, research
  notes, investment write-ups): DeepSeek, through Magpie in Claude Desktop or through a CLI runner.
- **Private data that must not leave the Mac:** local Llama, once a model is installed. Say so if none is.
- **Never decide money for the owner.** For investment work, DeepSeek or any model gathers, compares and
  drafts; the owner makes every buy or sell decision. Cite sources and dates; flag stale data.

## Routing an mstack issue
- An issue's worker host comes from its plan (`--agent`) and `taskboard.workers`. Desktop hosts
  (`claude-desktop`, `codex-desktop`) open a session; CLI hosts (`dsh`, `opencode`) run headless in the
  task worktree and report with `note`/`done` like any worker.
- `dsh` (DeepSeek V4 Flash by default) only after the owner's 👍 on a real run (MST-62's first-run ask): until then,
  don't put `dsh` in `taskboard.workers` or a plan's `--agent`. Then: `--agent dsh`, first plan line
  `Model: DeepSeek V4 Flash (dsh headless)`. Its session shows in "My tasks" as `dsh:<id>`, linked to its run log.
- Put the model in the plan's first line, e.g. `Model: DeepSeek (via OpenCode)`, so the owner approves it with the plan.
- If the chosen route isn't available, say which one is missing and propose the next best. Don't
  quietly fall back to another model.

## Boundaries
- Installing OpenCode, starting DeepSeek Harness's profile, downloading Llama weights, enabling Codex through
  Magpie, or changing Claude Desktop's active profile are setup steps. Load
  `.agents/skills/mcp-stack-setup-guard/SKILL.md` and get the owner's explicit OK for each one.
- Switching Claude Desktop between the official profile and Magpie is the owner's action, done in the app. Don't
  do it from a session. The two profiles keep separate data folders; running both at once is unverified.
- Paid API calls (DeepSeek) are fine once the owner has chosen DeepSeek for the task; keep them to the task.
