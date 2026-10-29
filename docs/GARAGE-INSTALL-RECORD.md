# Garage installation record

## Retained-state recovery — 2026-10-09

The user requested restoring the absent container/image. Its original pinned
2.3.0 image and matched metadata/data/RPC-secret state were reused after a verified
offline backup. Only the missing `mcp-stack-n8n-local` network and the `garage`
container were recreated. Original node, bucket and both client keys remain;
both keys pass read-only S3 object-list requests. No n8n container or application
binding was started or imported. See [the recovery report](SERVICE-RECOVERY-2026-10-09.md).

## Original installation — 2026-10-05

Completed2026-10-05 after explicit user approval. Runtime is the existing macOS
OrbStack Docker engine; definitions and private state live in this repository.

## Installed

- Official Garagev2.3.0, native ARM64 manifest
  `sha256:2d3f94a89a8a02dc49fa75594d6df67ed9c6ffe08fe55ed023d0c9776f71a9bd`.
- Compose project `mcp-stack`, service `garage`, container `mcp-stack-garage`.
- macOS `127.0.0.1:53900` ->3900. RPC stays on container loopback; no admin/web ports.
- Named volumes `mcp-stack-garage-meta`, `mcp-stack-garage-data`.
- Existing networks `mcp-stack-memory` and `mcp-stack-n8n-local` joined by Garage.
- Bucket `project-mcp-stack-demo-artifacts`; distinct Windmill/n8n read/write keys.
  No bucket-owner grants; no project outside the demo automatically provisioned.
- Original RPC secret `infra/garage/state/rpc-secret`0600; Compose runtime env
  `infra/garage/state/runtime.env`0600, directory0700. The same secret is supplied
  as `GARAGE_RPC_SECRET` to the process, not printed or included in versioned files.
  Docker engine administrators can inspect container environment; this is the
  local deployment's credential boundary, not a hardware-backed vault.
- Private client connection JSON/key records under the same state directory0600.
  `windmill-resource.private.json` and `n8n-resource.private.json` contain the
  ready-to-enter connection fields. They are not imported application resources.

No new host packages, PostgreSQL changes, gateway/harness registrations,
unrelated model calls or old-data migration. All25 pre-existing containers retain
their identity, start time, status, mounts and network membership, including
stopped {{mstack:CLIENT_REPO}}. Mount ordering was normalized for this comparison; an initial
raw-list comparison falsely reported graph mount-order differences.

## Verification

- Container health `healthy`, `garage status`: one assigned healthy node,
  runningv2.3.0. Published S3 port is loopback-only.
- [Synthetic acceptance](../integrations/garage/smoke.py) ran using the existing
  Windmill worker Python3.13.5 and n8n Node26.7.0, without package installation.
- Windmill PUT -> n8n GET; n8n PUT -> Windmill GET; bytes matched.
- Authenticated object listing succeeded; anonymous GET returned403.
- A second temporary project key could access its own bucket. Both demo service
  keys were denied403 against that project; the second key was denied403 against
  the demo project. This qualifies bucket/key isolation for those cases.
- Both exact test object keys were deleted and returned404; temporary bucket/key
  removed. Durable demo bucket and service keys remain.
- macOS S3 endpoint returned403 unauthenticated, as expected.

Private baseline/result: `infra/garage/state/install-baseline.json` and
`install-result.json`. No secret values in the public evidence.

## Corrections during installation

The initial tmpfs list needed quoting so YAML commas did not become mount paths.
After that correction, the dropped-capability root process could not read an
owner-only bind secret owned by501. A restricted group-readable copy was tried,
but Garage requires0600 even though its message calls the file world-readable.
That failed copy was removed; the final deployment uses a private Compose env
file and keeps capabilities dropped, without a permissions-check exemption.
Only the new Garage container was created/recreated during correction; its final
start is healthy and the data volumes persisted throughout.

`macctl` rewrites standalone absolute path arguments; therefore container CLI
commands use `./garage`, not `/garage`. Compose's in-container command/healthcheck
keep `/garage` because YAML strings are not macctl argv translations.

## Remaining app bindings

Network access and S3 permissions are verified. The user subsequently requested
S3 bindings: n8n's generic credential is registered through its supported CLI;
Windmill's resource awaits an authenticated workspace token. Workflow acceptance
has not run. No stored login was bypassed, no owner password read and no
internal app tables edited directly. See [binding evidence](GARAGE-S3-BINDINGS.md)
and [the connection guide](GARAGE-SETUP.md).

## Operations and rollback

Read-only status:

```sh
macctl run docker exec mcp-stack-garage ./garage status
macctl run docker exec mcp-stack-garage ./garage bucket list
```

The correct scoped Compose command for a subsequently approved lifecycle action:

```sh
macctl run docker compose -p mcp-stack --env-file infra/garage/state/runtime.env -f infra/garage/compose.yaml up -d --no-deps --pull never garage
```

Data-preserving rollback stops/removes only `mcp-stack-garage`; keep both volumes,
RPC secret, private runtime env and connection records. No cleanup is required
after successful acceptance; destructive volume deletion is not rollback.
Single-node storage has no redundancy. A matched offline backup was verified
during October 9 recovery; replay into an isolated target remains untested.
Follow the setup guide's matched metadata/data/secret backup boundary.
