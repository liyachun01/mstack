# Knowledge organization — preserve sources, curate knowledge

Updated 2026-10-06: Anytype is the sole PKM; Basic Memory is secondary and
ai-memory an experimental working-memory candidate. No automatic import/mirror.
Decision: 2026-10-05. Use a light, faceted catalog rather than relocating the
repository or introducing another knowledge application.

## Method

Use **PARA** for purpose/lifecycle: Projects (bounded outcomes), Areas (ongoing
responsibility), Resources (reusable knowledge), Archives (inactive history).
Use **Diátaxis** for the kind of technical document: tutorial, how-to, reference,
explanation. Record architectural decisions as short dated decision records.
This is a practical combination, not a claim of a scientifically proven best
classification. The two schemes answer different questions and can be tags.

Sources: [PARA, Tiago Forte](https://fortelabs.com/blog/para/) and
[Diátaxis](https://diataxis.fr/).

| Example | PARA | Document kind | Canonical source |
| --- | --- | --- | --- |
| Windmill shared-PG replacement | Project, archive after completion | Decision + how-to | `docs/WINDMILL-SHARED-PG-PROPOSAL.md` |
| Operating the personal stack | Area | How-to | `docs/START-HERE.md` |
| Database roles and persistence layout | Resource | Reference | Reviewed `infra/` files and database docs |
| Why Codex is primary / graph tools optional | Area | Decision/explanation | `AGENTS.md`, `docs/MEMORY-ROUTING.md` |
| Completed Windmill trial | Archive after retirement | How-to + verification evidence | Existing trial proposal/runbook and Compose |

## Keep one authoritative copy

- `infra/`: executable runtime definitions, retained at their existing paths.
- `integrations/`: reusable implementation, tests, portable scripts/workflows.
- `docs/`: engineering guidance, decisions, catalogs and historical evidence.
- `knowledge/main/`: future curated Basic Memory notes linking to these sources.
- Anytype: canonical user/project knowledge in the bound Space, initially
  local-only. Notes link to engineering sources; do not relocate runtime files.
- Basic Memory: retained existing Markdown context, secondary/opt-in.
- ai-memory: optional working context/checkpoints, not a duplicate canonical PKM.
- Notion/AppFlowy integrations are excluded; historical evaluations remain.

Do not bulk-ingest `infra/`: it also contains ignored state, credentials, vendor
assets and logs. Later import only reviewed Markdown summaries and selected
sanitized configuration excerpts. Secrets, `.env`, state, database dumps, auth
sessions, raw execution logs and private payloads are excluded even when Git
ignores them. Preserve originals; archival is a catalog status, not deletion.

## Minimal metadata for a future note

```yaml
id: mcp-stack-windmill-shared-pg
area: personal-agent-platform
para: project
kind: decision
component: windmill
status: proposed
source: docs/WINDMILL-SHARED-PG-PROPOSAL.md
verified_on: 2026-10-05
```

Use status values `proposed`, `active`, `optional`, `superseded`, `archived`.
A proposal must never be retrieved as an executed deployment. Add source revision
or checksum when importing; keep stable source links and a supersedes relation.
Refresh a note when its source changes, not on every chat. Do not invent an
embedding/indexing requirement. No Basic Memory or external PKM writes were made.
