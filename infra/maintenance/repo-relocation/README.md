# Repository relocation — 2026-10-19

Canonical checkout: `/home/developer/workspace/mstack`.
The former `mcp-stack` directory was already renamed before this audit. The
sibling was a symbolic link to this exact directory, created to keep old Codex
chats usable. It is now removed. There was no independent source copy to compare.

The pre-edit inventory contains 75,247 regular files and 1,086 symbolic links,
including Git metadata, ignored/private state, AGENTS.md, project skills,
`.mstack`, `.serena`, documentation, and retained runtime dependencies. File
hashes, modes, sizes, and inode identities are saved privately in `.state/`.
Git has no commits; no commit history was removed by this work.

## Completed

- Verified old and new paths refer to the same directory.
- Corrected operational host paths in entry documents, scripts, the inactive
  n8n workflow, the retained Llama preferences template, and recovery pointer.
- Retargeted all 430 existing DeepSeek profile links to the same dependency
  tree. The 96 previously missing targets remain exactly the same; no package
  install or provider call ran.
- Updated Serena's existing project registration to the new root.
- Inventoried all 96 relevant Codex records: nine user chats, seven historical
  subagents, and 80 review records. All histories exist, including two compressed
  archives. These histories live under `~/.codex`, independently of the checkout.
- Recreated the six affected containers below at the new bind paths, keeping
  them stopped. Exact image IDs, environment, mount permissions, data volumes,
  resource limits, and network choices are verified. The other 24 containers
  retain their identities, settings, mounts, networks, and state.
- Merged eight existing desktop chat assignments into the new project entry,
  preserving chat IDs, project ordering, and pin state. Restarted ChatGPT Desktop
  and verified the merge persisted through both its settings file and app API.
- Removed only the old sibling symlink after the runtime and desktop checks.
  Removed six obsolete mise trust-path links after verifying all six replacement
  trust entries already existed. Rollback mappings are saved privately.
- Local workflow tests (25), launcher tests (14), and mstack plan/doctor pass.

All nine user chats now use mstack. Supported-API migration preserved their
IDs, archived status, and every original history byte (verified as an unchanged
prefix). See `.state/codex-user-chats-verified.json`. Historical subagent/review
records remain preserved in the same Codex store. All 96 original history
prefixes and archived states were reverified after the cutover. Three historical
child paths were also updated through their parent; other child/review cwd fields
remain historical metadata, accessible with thread/read. No histories were rewritten
or new agent/model turns started.
Historical audit/command text and container-internal graph paths intentionally
retain their original spelling; those are not dependencies on the host alias.
Stable project/service/volume identities remain `mcp-stack` where already used.

## Completed cutover

The user explicitly approved the remaining container migration, desktop restart,
and alias removal with “do”. All steps completed on 2026-10-19. There is no
pending approval or cleanup action.

Desktop settings were changed while its actual settings-writer processes were
closed. An initial check also counted orphaned crash reporters, so that attempt
made no settings changes; the corrected check excludes them. The successful
merge is backed up privately and remains present after restart. All nine original
user chats have their original histories and archived status.

All 30 containers remain stopped. The six affected containers have new IDs and
status `created`; their image IDs, names, credentials, persistent mounts, network
choices, ports, and effective resource settings match the before snapshot. Docker
regenerated Compose hashes/replacement labels, normalizes unset OOM-kill-disable
to false, and leaves network endpoint IDs empty before the first start. Existing
network IDs are unchanged. Gateway and PostgreSQL Compose working-directory
labels now correctly record the repository root. Other retained containers may
still have historical Compose labels; their bind mounts do not depend on the
removed path. Operate them from the current repository definitions.

These are the exact executed migration commands, retained as evidence. They are
not startup commands; do not repeat a completed migration.

```sh
docker compose -p mstack \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mstack/infra/services/compose.yaml \
  create --force-recreate --no-build --pull never headroom anytype-mcp graphify

docker compose -p mstack \
  --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mstack \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mstack/infra/agentgateway/compose.yaml \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mstack/infra/agentgateway/projects/compose.yaml \
  create --force-recreate --no-build --pull never agentgateway

docker compose -p mstack \
  --env-file /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mstack/infra/garage/state/runtime.env \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mstack/infra/garage/compose.yaml \
  create --force-recreate --no-build --pull never garage

docker compose -p mstack \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mstack/compose.yaml \
  create --force-recreate --no-build --pull never postgres
```

Verification receipts and private before/after snapshots are under `.state/`.
Final filesystem checks found no missing project/private files, changed runtime
data/dependency contents, or changed Git objects. Codex pruned eight temporary
checkpoint/ref entries under `.git/refs/codex/turn-diffs/` during session lifecycle;
these are app-maintained transient metadata, not repository commits.
Container filesystem diffs contained only mount placeholders, runtime directories,
and OrbStack-injected certificates/init support; application data remains in the
same persistent volumes or bind files. No volume reset or data migration ran.

Rollback records preserve original desktop settings, symlink targets, source-file
copies, container definitions, and the prior pinned images/data volumes. Restoring
an old path would require explicit maintenance; do not recreate the alias as a
routine startup action. The migration helpers fail closed on completed targets.

No service start, database migration, new index, example restoration, model
download, inference, external document write, or schedule is part of this work.
