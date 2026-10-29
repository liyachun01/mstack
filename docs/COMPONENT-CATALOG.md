# Component catalog

Current 2026-10-06 state/flow is in [the canonical handover](HANDOVER.md).
Anytype is sole PKM; Notion/AppFlowy excluded; Basic Memory secondary; ai-memory
installed candidate. Previous runtime-health observations below are historical:
existing containers are currently stopped and were preserved by this work.

Decision and read-only runtime inventory: 2026-10-05. Categories describe intent;
Classification alone changes no process. The separately approved Windmill
replacement and Activepieces retirement are now complete. All existing `infra/`
entries and their source history remain in place.

| Capability | Default / expansion | Observed state | Source / reference |
| --- | --- | --- | --- |
| Interactive harness | Codex default | Current entry point; stack registration pending | `AGENTS.md` |
| Alternate harness | DeepSeek, OpenCode optional | Existing DeepSeek preserved; OpenCode not inventoried | `infra/harnesses/deepseek/` |
| Database | Shared PostgreSQL foundation | PG18.6 healthy; Basic Memory/n8n isolated DBs | `infra/postgres/` |
| Workflow execution | Windmill primary | Shared PG deployment healthy; trial runtime/data removed | `infra/windmill/`; [proposal](WINDMILL-SHARED-PG-PROPOSAL.md) |
| Historical proxy option | MetaMCP superseded | Not deployed; no replacement planned | [historical assessment](METAMCP-SETUP-PROPOSAL.md) |
| Selected proxy | agentgateway | Running; preserve existing graph routes and DeepSeek integration | `infra/agentgateway/` |
| Graph context | Graphify retained, used when relevant | Backend running; narrow approved index | `infra/graphify/` |
| Durable documents | Basic Memory retained | Healthy; PG and Markdown persistence; Codex connection pending | `infra/basic-memory/`; `knowledge/` |
| Source graph | CodeGraph optional | Backend running; no broad indexing allowed | `infra/codegraph/` |
| Maintained wiki | OpenWiki optional | Not installed in this task | [upstream](https://github.com/langchain-ai/openwiki) |
| Connector workflows | n8n optional | Healthy at macOS5678; existing dry-run workflow retained | `infra/n8n/`; `integrations/n8n/` |
| Alternate workflows | Activepieces excluded | Test containers, data volumes, network and env removed; definitions retained | `infra/activepieces/`; [record](ACTIVEPIECES-RETIREMENT.md) |
| Optional platform | Supabase deferred | This project's option disabled; unrelated {{mstack:CLIENT_REPO}} protected | `infra/supabase/` |
| PKM | Anytype only | macOS client downloaded per user; local-only selected; MCP/Space binding pending | `infra/anytype/` |
| Working memory | ai-memory experimental | 2.5.2 healthy, direct MCP qualified; no hooks/providers/harness registration | `infra/ai-memory/` |
| Retired PKM choices | Notion/AppFlowy excluded | No integration planned; historical definitions/unrelated data preserved | [knowledge policy](KNOWLEDGE-ORGANIZATION.md) |
| Host tool selection | Existing tools only | No toolchain changes | `infra/mise.toml` |

## Progressive use

1. **Direct work:** Codex plus project files. No service dependency for a simple task.
2. **Remember or connect evidence:** use relevant Basic Memory/Graphify capabilities
   only after the required connection is qualified; do not block ordinary work on it.
3. **Repeat execution:** use Windmill for a concrete script/job that benefits from
   recorded inputs/results, scheduling or retries. Start with one worker.
4. **Expand for a named gap:** alternate harness, n8n connector, source graph, wiki,
   PKM integration. A catalog entry is not an installation backlog.

Workflow engines complement one another through explicit inputs/outputs such as
JSON and HTTP; n8n/Activepieces definitions are not binary-compatible Windmill
flows. Preserve portable business logic in `integrations/`, runtime wiring in
`infra/`. No compatibility adapter or financial workflow is implemented here.

Completed footprint reduction: removed three Windmill trial and four Activepieces
containers; added two Windmill processes using shared PG. Net five fewer containers
and three fewer volumes. Marking n8n/CodeGraph optional does not stop them; their
lifecycle remains unchanged.
