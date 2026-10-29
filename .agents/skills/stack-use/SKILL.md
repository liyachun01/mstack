---
name: stack-use
description: Compatibility entry for the mstack project workflow. Use the smallest project preset and qualify only the tools needed.
---

# mstack compatibility entry

Read `../mstack/SKILL.md` relative to this skill directory. Use the repo-local
`mstack` CLI; `stack` remains a compatibility alias. Existing `.mstack/stack.json`
is the editable intent; generated records live in `.mstack/state.json`.
Older project registry/binding files and examples are retired. Default to `daily`.

The everyday channels are Codex/Claude, Anytype, and Windmill when useful.
Do not mirror Anytype into a memory store, require graph retrieval, or reindex
as a startup step. Explicit writes require readback in the bound project channel.
No credential or grant is inherited by a fresh project.

Runtime changes follow `../mcp-stack-setup-guard/SKILL.md`, honoring existing
user authorization. Preserve system tools, shared resources and project data.
Do not install missing tools or restart services as init/doctor actions.
