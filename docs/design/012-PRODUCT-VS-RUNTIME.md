# 012 — mstack itself vs this installation's records (proposed, 2026-10-29)

Status: rule in force from now on; moving existing files is MST-22.

mstack now has a repo, users ({{mstack:CLIENT_REPO}}, {{mstack:CLIENT_C_SITE}}) and a running installation, but one tree holds two different
things:

| | **mstack (the product)** | **Runtime (this installation)** |
|---|---|---|
| What | code, schemas, skills, service definitions, design and how-to docs | what happened on this machine: install, retirement and recovery receipts; qualification results; dated decisions and handovers; proposals that were applied or dropped |
| Changes when | mstack gains or changes a feature | something is installed, removed, repaired or decided here |
| Who reads it | anyone running mstack, every agent working on it | the owner and ops sessions on this machine |
| Ships | yes, could be shared one day | never; stays private |

## Layout

```
mstack/
  integrations/   product: code, tests, schemas, plugin manifests
  .agents/skills/ product: mstack-* skills (setup guard included)
  infra/          product: service definitions only (compose files, presets, config templates)
  docs/           product: design (docs/design/), guides, references
  mstack, stack   product: CLIs
  runtime/        runtime: everything about this machine
    AGENTS.md     standing rules for this installation (don't reinstall X, protected tools, accounts)
    journal/      dated notes, one file per day (today's AGENTS.md history moves here)
    receipts/     install, retire, recovery and qualification records (today infra/maintenance/, */qualification.json, */resume-*.json)
    docs/         proposals, corrections, install records, handovers, status and TODO pages
  .mstack/        mstack's own board config and private state (ignored parts stay ignored)
```

Secrets and service state stay where they are: ignored, never in git (`.secrets/`, `*/state/`).

## Rules (in force now)

1. **A new record goes to `runtime/`:** a receipt, a dated note, a proposal, a status page. Not `infra/` or `docs/`.
2. **A new feature goes to the product folders.** Its design goes in `docs/design/`, its how-to in `docs/`.
3. **Product never depends on runtime.** No code imports or reads a receipt. A one-off migration helper that
   writes receipts takes the output folder as an argument, defaulting to `runtime/receipts/`.
4. **AGENTS.md stays short:** how to work on mstack, plus a pointer to `runtime/AGENTS.md` for this machine's
   standing rules. Ops sessions and the setup guard read both.

## Migration (MST-22)

- **Receipts:**
  - Move `infra/maintenance/**` → `runtime/receipts/maintenance/`.
  - Move the qualification and resume JSON files under `infra/*` → `runtime/receipts/<component>/`.
  - Leave a short README behind wherever a folder empties.
- **Docs:** move the dated and proposal docs (`docs/*-PROPOSAL.md`, `*-CORRECTION.md`, `*-RECORD.md`, dated
  reports, `HANDOVER.md`, `SETUP-STATUS.md`, `TODO.md`, the side-chat handoff) → `runtime/docs/`.
- **AGENTS.md:** split it. The dated history goes to `runtime/journal/`, the standing rules to
  `runtime/AGENTS.md`, and the remainder becomes the short product guide.
- **References:**
  - Rewrite links and paths, including the setup guard skill, the READMEs and the helpers under
    `integrations/{n8n,windmill,toolchains,ai-memory}` that write into `infra/maintenance`.
  - `mstack proof` evidence paths in project state must still resolve.
- **Checks:**
  - `git mv` only, so history follows.
  - Run every test suite.
  - Run `mstack doctor` and `mstack proof` for each project.
  - `./mstack hydrate --check` before pushing.
- **Not in scope:** splitting runtime into its own repo. With the folder boundary that's a later
  `git subtree split` if it's ever wanted.
