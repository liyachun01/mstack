# Activepieces test environment — retired

2026-10-05. User explicitly excluded Activepieces and approved deleting its test
environment/data. Removal ran on macOS OrbStack through existing `macctl run`.
No new installation, package manager, image pull or broad Docker prune.

## Exact removal

Preflight verified Compose project labels, source file, mount ownership and
absence of unrelated volume/network consumers. Removed:

- `activepieces-worker-1`, `activepieces-app-1`: observed image0.92.1.
- `activepieces-postgres-1`: observed pgvector0.8.0/PG14 image.
- `activepieces-redis-1`: observed Redis7.0.7 image.
- Volumes `activepieces_postgres_data`, `activepieces_redis_data`.
- Network `activepieces_activepieces` and runtime
  `infra/activepieces/activepieces/.env` (not read or copied for cleanup).
- Verified bind cache `infra/activepieces/activepieces/cache` empty; retain the
  empty directory. No cached entries required deletion.

Exact lifecycle commands were stop, then rm for the four named containers,
volume rm for the two named volumes, and network rm for the named network.
No surviving containers mount its cache. Final project-label searches find no
Activepieces containers, volumes or networks. Its former host8080 listener is gone.
Definitions remain at `infra/activepieces/activepieces/docker-compose.yml`.
Shared images were not pruned; images are not retained application database state.

Data deletion is irreversible without a pre-existing backup; none was created.
The retained source can support a separately requested fresh deployment with new
credentials, not restoration of the old flows/users/history.

Combined with Windmill trial retirement: seven containers/five volumes/two
networks removed, two replacement Windmill containers/two cache volumes created.
Net container count29→24. All22 unrelated containers and17 other volumes retain
baseline metadata. {{mstack:CLIENT_REPO_TITLE}}, other Supabase projects, AppFlowy volumes, optional
n8n/CodeGraph, Graphify, Basic Memory, shared PG and agentgateway were preserved.
Private evidence is under `infra/windmill/state/replacement-3411t0az/`.

## Should it replace or complement Windmill and n8n?

**Recommendation for this user's small stack:** keep Windmill primary and n8n
optional. Leave Activepieces excluded. Revisit it as an alternative to n8n only
when a specific connector or builder experience clearly improves a real workflow.
Adding it alongside both engines duplicates much of the connector orchestration
and adds another application's credentials, queues, database and upgrades.

This is a fit judgment, not a measured performance comparison:

| Tool | Role to evaluate | Decision here |
| --- | --- | --- |
| Windmill | Code-first scripts, typed inputs, workers and composed workflows | Best match to the stated code/data-processing direction; retain |
| n8n | Visual app integration and business-process workflows | Existing optional connector complement |
| Activepieces | Trigger/action app flows and agents | Potential substitute for the connector layer, not needed as a third engine |

Activepieces documents app/worker components plus PostgreSQL and a Redis queue;
its introductory docs emphasize app-connected agents and flows. Windmill documents
multi-language script execution and worker-based workflows. These capabilities
support the division above; connector fit and free-edition restrictions should be
checked against an actual future workflow, not assumed from product headlines.

Sources reviewed2026-10-05: [Activepieces overview](https://www.activepieces.com/docs/getting-started/introduction),
[Activepieces architecture](https://www.activepieces.com/docs/install/architecture),
[Windmill introduction](https://www.windmill.dev/docs/intro),
[n8n documentation](https://docs.n8n.io/).
