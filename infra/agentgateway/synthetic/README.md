# Disposable gateway qualification fixtures

See the [proposal and approval boundaries](../../../docs/AGENTGATEWAY-SYNTHETIC-PROPOSAL.md).

Approval A completed: project-only files/hash configuration created; fixture
started, directly tested and removed. No published ports or real memory access.
The existing Graphify image supplies Python + official low-level MCP SDK; Graphify
itself is not launched/imported. No installation/build/download is performed.

Use existing macOS OrbStack Docker through `macctl run docker compose`, explicitly
targeting project `mcp-stack-gateway-test`, this overlay, and the macOS repository
path as `--project-directory`. Never combine this overlay with root Compose.

Run direct tests only while the approved fixture is running:

```sh
python3 infra/agentgateway/synthetic/verify.py --fixture-only
```

`prepare.py` refuses existing output and never rotates the foundation key.
State/config stays in ignored `../state/synthetic/`. The fixture mounts only
`fixture.py` read-only; counters and outage controls are RAM-only. Network
`mcp-stack-gateway-synthetic` is a normal bridge (outbound possible, no external
calls configured), retained empty after scoped cleanup for diagnosis.

Approval B was authorized by “Now contnue!”: the isolated gateway started on
58081 with the exact official 1.5.0 image, tested, then removed with the fixture.
`verify.py` now implements both fixture-only and bounded gateway modes.
Live gateway on 58080 and all memory/database/harness configurations stayed unchanged.

Verified: both fake endpoints initialized MCP 2025-11-25 and passed tool/prompt/
resource discovery/dispatch, Host/Origin rejection, independent beta outage/
recovery and counter reset. Runtime: Python 3.12.14 / SDK 1.29.0 / Starlette 1.3.1 /
uvicorn 0.47.0. All 19 pre-existing container snapshots and 260 protected file
hashes unchanged; checked macOS mise/Codex config unchanged; foundation HTTP
checks passed again. Network retained empty; ignored config retained.

Initial gateway run hit HTTP 421 due to internal Host `fixture` versus the
original port-qualified allowlist. The user separately approved adding that
exact hostname, retaining DNS/Origin protection. Direct positive/negative Host
checks and all **eight gateway tests passed** on retry, including actual
concurrent session calls, replay rejection, pre-dispatch denials and fail-closed
outage/recovery. See the [correction and results](../../../docs/AGENTGATEWAY-SYNTHETIC-HOST-CORRECTION.md).

Both test containers removed; network empty. All 19 pre-existing container
snapshots/260 protected hashes and checked macOS configs unchanged again;
foundation HTTP checks passed. For a later approved retry reuse generated
config; do not rerun `prepare.py`. Container version diagnostics use
`./app/agentgateway`, not an absolute path subject to macctl translation.

Qualification is synthetic only. No real server/harness connected; live 58080
`/mcp` is still the intentional 503 placeholder. Re-running these lifecycle
commands needs its own approval; there are no permanent test services/watchers.
