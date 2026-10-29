---
name: computer-use
description: Operate mcp-stack example projects and authorized native desktop harness setup. Use for guided project exercises, Anytype UI fallback, or Claude Desktop gateway setup and verification; respect project presets and the setup guard.
---


## OpenCodex removal completed — 2026-10-21

The user subsequently requested removing OpenCodex. This supersedes all older
OpenCodex retention/rollback instructions in this skill. Its stopped container,
two dedicated volumes, unused image, credentials, setup files and old native
Claude profile are removed, including dedicated credential/profile backup copies
and Magpie's old applied-profile stash pointer. Do not restore or reinstall it.

Claude Desktop still uses Magpie/official DeepSeek; Codex integration is pending
explicit request. Native Codex config/auth and the active Magpie profile/provider
are unchanged. All 31 other containers present at removal and unrelated data are
preserved. The old custom Codex project routes remain unbound; no Magpie binding
is inherited. Use `integrations/models/magpie_manage.py` for local operations;
the one-time migration helper is retired. No new quiet UI window is active.
See `infra/maintenance/opencodex-retirement/README.md` for exact targets and proof.

# Background-only preference — 2026-10-16

The user is actively using the Mac. Use APIs, containers and isolated headless
browser sessions. Do not activate apps, move windows, send desktop input, wake or
hold the display. Native UI setup waits for an explicitly arranged quiet slot or
manual user setup. This supersedes the proactive foreground UI fallback below.
The October 16 quiet windows covered specific setup and example retirement.
Those actions are complete; return to background operation.

# Operate an example project

This is a repository-local skill. No existing `computer-use` skill was found when
this version was created; it does not modify a global skill or supply a GUI tool.
Use actual available file, shell, browser and MCP tools, not simulated operations.

## Claude Desktop through Magpie — 2026-10-21

The installed surface is Claude Desktop 3.1623.0, not a new Claude Code CLI.
The user explicitly migrated it from OpenCodex to installed Magpie 0.1.1206.
Codex integration is pending until requested. Read the setup guard,
`infra/claude-desktop/config.json`, and `infra/magpie/README.md` before changes.
This supersedes the October 8 OpenCodex selection for current Claude operations.

Claude uses native third-party gateway mode at Mac loopback 3425 with the existing
official DeepSeek Flash provider. Magpie's built-in adapter manages the generated
native `Claude-3p/configLibrary`; it is a real Mac directory because its atomic
metadata writer fails through the OrbStack mount. Runtime intent and private
Magpie state stay under `infra/`. Preserve all unrelated profiles and settings.
No app patch, certificate changes, shell configuration or account login is needed.
The provider key remains private; the Desktop token is a public local caller
marker. Keep the visible model label DeepSeek; a Claude-shaped wire alias does
not make it an Anthropic model or qualify every advertised capability.

Streaming and automatic synthetic tool/result handling passed. Management returned
401 without its key and 200 with it. The native window was not opened during this
migration. Actual chat rendering, Code/Cowork file access, project MCP and Anytype
grants require their own qualification when relevant. The completed paid protocol proof remains historical evidence. Use
`integrations/models/magpie_manage.py verify` for local checks without inference.
The old OpenCodex helpers and the one-time migration helper are removed.

Native UI actions still need an explicitly arranged quiet window. During one,
inspect observed controls through System Events and the existing Claude UI helper;
restore temporary AXManualAccessibility/AXEnhancedUserInterface values. Do not
inspect credential dialogs or change macOS security permissions. No quiet window
is currently active. Keep background operation while the user uses the computer.

At migration time all 33 containers were unchanged. OpenCodex was subsequently
removed on request; the other 31 containers present at removal stayed unchanged. Magpie's account discovery, updates, fallback and archives are off.
Do not connect Codex or reuse another project's document grant.

## Native Anytype UI fallback

When the user authorizes creating a project channel, create a dedicated personal
channel yourself rather than requiring an existing destination. Check the running
macOS app and existing Accessibility access through `macctl` first.
`integrations/computer-use/anytype_ui.applescript` operates observed native controls
through System Events. Temporarily enabling the app process's
`AXManualAccessibility` may be necessary; restore its original value afterward.
Do not change global security permissions or use voice-only screen capture in a
text conversation. Never inspect recovery keys or existing credentials.

Create a new API v2 key for that project channel only; leave all-spaces access
off. Save the newly created key directly to its ignored private credential file,
never the clipboard, chat or source. Verify the authenticated full Space ID and
grant before content operations. Qualify direct MCP separately from UI creation.
The project stdio launcher/client is `integrations/agents/anytype_mcp.py`, backed
by the shared authenticated Anytype tenant. Read the selected project's
`.mstack/stack.json` and generated `.mstack/state.json`; never read a retired
legacy registry or borrow another channel/key. Use `mstack doctor` for local
consistency, then scoped live calls/readback for actual qualification.

The example projects are retired. Do not recreate them or restore their revoked
grants. Ordinary project document work is background-only. The approved quiet
window for deleting mstack-example ended after its channel/key were removed.
No standing permission to control the desktop follows from that completed work.
