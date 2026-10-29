# Sharing tool setup without sharing private memory

Decision (2026-10-01): the pre-existing Ubuntu user-level Graphify 0.9.39 belongs to the {{mstack:CLIENT_REPO}} workflow and stays untouched. This project uses its own pinned container. Keeping {{mstack:CLIENT_REPO}}'s setup in that repository is a later repo-scoped task; no relocation or {{mstack:CLIENT_REPO}} edits are authorized here.

External memory does **not** require externalizing tool configuration or making the agent's private history the team's source of truth. Separate reproducible setup, reviewed knowledge, and generated/private state:

| Category | Recommended ownership / sharing |
| --- | --- |
| Dockerfiles, Compose, version/commit/digest pins, tool gates, verification scripts, routing instructions, secret-free templates | Version-controlled in the owning repository, under `infra/` for tool configuration. `AGENTS.md` and local skills use their discovery paths. |
| Approved team architecture decisions, runbooks, conventions, incident learnings | Reviewed Markdown in the owning repository, e.g. `docs/decisions/`; commit through ordinary review. Memory/PKM can index or mirror these documents, but does not silently replace them. |
| Graphify/CodeGraph indexes, caches, transient session context | Per developer and per repository, ignored and rebuildable from a defined source scope. Do not commit machine-dependent indexes by default. |
| Personal Basic Memory notes, secrets, database files/dumps, harness history | Private and ignored. Shared knowledge must be deliberately selected/redacted, not copied wholesale from personal memory. |

## Recommended default: one local runtime per developer

1. Clone the project with its pinned setup definitions, routing instructions and canonical team documents.
2. Review the documented prerequisites and approved install procedure; supply local secrets through ignored files. A fresh clone must not depend on another developer's home directory or remembered conversation.
3. Build the same pinned tools and regenerate local indexes for an explicitly selected source revision/scope. Revalidate when the source or tool version changes.
4. Use project-scoped harness configuration when that harness supports it. Generate local machine paths from checked-in secret-free templates; do not commit personal tokens or absolute home paths. This stack's harness registration is not implemented yet.
5. Review changes to versions, tool permissions and durable team knowledge in Git. Private memory remains an assistant aid, not an authority that overrides source or reviewed decisions.

This avoids needing a central team memory service initially. Multiple developers may produce different private notes and indexes; consistent source, pins and policy matter more than byte-identical generated graphs. Record the indexed source revision/scope rather than assuming a graph is current or complete.

## What this repository already does, and what it does not yet do

- Docker/Compose definitions, pinning, tool filters, scripts, runbooks and routing policy are **not gitignored**. Runtime state, personal Markdown, secrets and backups are ignored. This is deliberate separation, not a requirement to keep setup outside Git.
- Existing `knowledge/` is personal and ignored; do not change that rule or publish existing notes to make a team corpus. If needed, create a separate reviewed team-document corpus in the relevant repository later.
- At the time of this setup, the repository files are still **untracked**, not committed or remotely shared. Preparing versionable files is not the same as committing/publishing them. No commit/push is performed without a request.
- Current smoke-test definitions include this OrbStack/macOS bridge, Linux ARM64 pins, fixed container projection paths and UID 501. They are reproducible for this environment, not a completed cross-platform onboarding package. Linux-native Docker, other architectures, developer UID/path parameters and project-scoped harness templates need a separately reviewed portability step.
- The global Graphify skill and {{mstack:CLIENT_REPO}}'s user-level CLI are not prerequisites for the new Graphify image: its build inputs and local adapter are defined in this repository. A teammate does not need this conversation or that global skill to reproduce the approved commands.
- Basic Memory remains personal and its further model/testing/harness/PKM setup is deferred. No shared Basic Memory service, multi-user isolation, synchronization or access-control guarantee has been implemented.

## Optional centralized sharing later

A shared service can be useful once the team needs synchronized curated knowledge. It is a separate deployment/security decision: authentication, permissions, per-project separation, backups, conflict handling and auditability must be verified for the selected product. A shared PostgreSQL instance or different schemas alone does not establish those guarantees. Do not expose the current loopback-only personal services or reuse {{mstack:CLIENT_REPO}}'s database to implement this implicitly.

For the current personal POC, prefer **versioned setup + reviewed repo documents + private local indexes/memory**. Evaluate shared PKM or a team memory endpoint only for a concrete collaboration need. The final standalone OrbStack/system workflow skill remains deferred; this document does not create or activate it.
