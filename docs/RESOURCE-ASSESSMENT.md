# Workload, battery and image cleanup — 2026-10-01

The user requested a workload assessment and unused Docker image/container cleanup, explicitly excluding stopped containers. Applied the project setup guard and careful-removal checks. No installation, service lifecycle change, runtime configuration change or gateway retry was performed.

## Measured workload

Mac host: 32 GiB RAM, 10 logical CPUs, on AC power and charging during inspection. The existing OrbStack machine `devbox` is running; Docker has **five running mcp-stack services and 16 stopped containers**. n8n, AppFlowy, local embedding/inference models and harness gateway integrations are not running as part of this stack, so their future workload is not measured.

After cleanup, collected four `docker stats --no-stream` snapshots over approximately **30.5 seconds**, with selected macOS process CPU-time deltas. No explicit MCP queries, indexing/model work, service restarts or memory usage tests were triggered. Existing scheduled health checks continued. This is a short low-service-activity observation during an active desktop session, not a controlled all-day idle benchmark.

| Service | Mean working set (MiB) | Mean CPU (100% = one core) |
| --- | ---: | ---: |
| codegraph-http | 120.8 | 0.003% |
| agentgateway | 23.8 | 0.150% |
| graphify-http | 69.0 | 0.297% |
| basic-memory | 238.8 | 0.472% |
| postgres | 38.0 | 0.000% |
| **Total** | **490.3** | **0.922%** |

Current service workload is small, but not zero-cost. [Docker's Linux memory figures subtract inactive file cache](https://docs.docker.com/reference/cli/docker/container/stats/), so this working-set total is not the entire RAM cost. Memory/CPU limits are ceilings, not reservations: e.g. CodeGraph's 2 GiB limit does not mean it continuously consumes 2 GiB.

In the same post-cleanup interval:

- The large OrbStack Helper process averaged **9.7% of one core** with approximately **9.34 GiB RSS** at the last snapshot. This includes the Docker engine, Linux machine and VM/kernel/cache overhead; it must not be attributed wholly to mcp-stack or added to the container memory total. [OrbStack runs Docker and Linux machines in a shared VM](https://docs.orbstack.dev/architecture).
- WindowServer averaged **27.5% of one core**, Codex Service **16.0%**, and an active Codex Renderer **9.1%**. These are active-desktop observations, not a full accounting of all host processes.
- Earlier maintenance-overlapping observation showed OrbStack Helper around 75% CPU; later load fell substantially. Do not use the pruning interval as the stack's steady idle cost, or claim the cause of remaining whole-VM overhead is established.
- Host swap usage was about 106 MiB. Guest `free` previously showed around 3.2 GiB used, 6.2 GiB buffer/cache and 12.8 GiB available; guest accounting is not equivalent to host RSS.

## Battery implications and recommendations (not applied)

Yes, keeping services/VM activity alive consumes power, but this sample does not show heavy CPU use by the five MCP services. Images and stopped application containers mainly occupy storage rather than running application CPU; deleting images is primarily storage cleanup, not a demonstrated battery optimization.

Observed macOS `pmset -g assertions`: **caffeinate PID 81298 held an indefinite PreventUserIdleSystemSleep assertion**, active for over an hour. The user subsequently confirmed it is deliberate to keep AI work running with the lid closed. **Preserve it; do not treat it as an unwanted battery problem or kill/reconfigure it.** This records intent, not a hardware/power-state validation of closed-lid operation. No assertion/process was changed.

The Mac is charging, so no defensible watts, battery-percent/hour or hours-lost estimate is available. For a real comparison, use [Activity Monitor Energy Impact/12 hr Power](https://support.apple.com/en-ca/guide/activity-monitor/actmntr43697/mac) and a controlled battery baseline under matched screen brightness/workload. Power monitoring or an A/B service-shutdown test would need a separate scoped plan; Basic Memory shutdown/reconfiguration remains deferred/protected.

Future battery review should focus on sustained whole-OrbStack/desktop load and an explicitly approved power profile, preserving the deliberate keep-awake requirement. PostgreSQL probes readiness every 10 seconds; Basic Memory launches its version health check every 30 seconds. These are potential recurring wakeups, not measured proof of the CPU cause. Do not adjust Basic Memory while deferred or replace its health check automatically. Graph watchers, automatic indexing and semantic search are already disabled/unconfigured. Large corpus indexing, local inference and a future multi-service PKM deployment need separate load qualification.

No sleep/power settings, CPU/RAM limits, model settings or service lifecycle changes were made. Moving host CLIs to mise does not eliminate Docker/VM power usage.

## Completed cleanup

Removed **27 distinct unused registry images (29 tags)** using explicit non-force `docker image rm` targets, after checking that no existing running or stopped container referenced their exact IDs. No broad `system prune`, `container prune`, force removal, volume/network/build-cache prune or package cleanup.

Targets include unused AppFlowy/MinIO, Budibase, Baserow, Outline, LiteLLM, Memos, Redis, Caddy, nginx, https-portal, Bash and unused PostgreSQL/pgvector versions. Those images were not used by any existing container; future use requires separately approved downloading again. AppFlowy's existing data volumes were preserved.

Preserved:

- **All 21 containers**, including all **16 stopped containers**, and every exact local image they reference. States/identities/start/health/ports unchanged; no restart/re-pull smoke test was performed.
- All Supabase images, including eight unreferenced versions/tools, to keep {{mstack:CLIENT_REPO_TITLE}} and its related recovery resources out of scope.
- The unreferenced custom `clientapp-media-transform:worker` image because pull/rebuild availability is not established.
- All 14 volumes, all network inventories and all 86 build-cache entries. No data, credentials, source indexes or notes removed; all **269 protected file hashes** unchanged.

Docker-reported storage:

| Resource | Before | After |
| --- | ---: | ---: |
| Images | 54 / 33.66 GB | 27 / 18.60 GB |
| Containers | 21 / 32.51 MB | unchanged |
| Volumes | 14 / 12.83 GB | unchanged |
| Build cache | 86 / 3.251 GB | unchanged |

Image-storage reduction is approximately **15.06 GB by Docker's accounting**, not a measurement of immediately reclaimed macOS filesystem blocks. `docker inspect` image sizes differ from `docker system df` accounting; do not sum compressed/logical sizes as guaranteed reclaimed storage.

Exact IDs/tags/registry digests and excluded images are retained in [the manifest](../infra/maintenance/image-cleanup-20261001.json); [results and service metrics](../infra/maintenance/image-cleanup-20261001.results.json) are also versionable and secret-free. There is no image archive or automatic rollback. Deleted images can be downloaded by their recorded registry digests if still available; restoring tags/versions and any pull require approval. Registry retention is not guaranteed.

The gateway remains Graphify-only, both graph backends running; the separately proposed CodeGraph gateway retry remains unapproved.
