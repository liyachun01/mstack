# Independent Claude Code CLI preparation

**2026-10-27 superseding update:** independent mise-managed Claude Code 2.1.310
and Codex were installed on both Mac and Ubuntu; both CLIs were uninstalled later that day.
Claude Max subscriptions are authorized through Edge on both hosts. The active
declarations, launchers, history safeguards and desktop-removal receipts now live
in [agent-clis](../agent-clis/README.md). This directory's proposal and templates
below are historical; do not install from its old Mac-only mise profile.

Prepared 2026-10-25. **No new installation or active profile binding.**
The user selected Claude and Codex subscriptions first, followed by DeepSeek API,
and explicitly selected Claude Code (CC) for the DeepSeek stage.

Updated 2026-10-26: the user prefers independent mise-managed CLIs on both macOS
and Ubuntu. T3 has been removed; Paseo and Paradev were later removed; Claude/Codex Desktop are back (2026-10-27).
See the [Superset removal record](../../maintenance/superset-retirement/README.md)
and [T3 removal record](../../maintenance/t3-retirement/README.md).
The pinned installation proposal below covers macOS only and has not run.

## Existing Desktop runtime found

The user clarified that CC Desktop already exists. Claude Desktop **3.6556.2**
has a native ARM64 Claude Code **2.1.308** runtime. Its macOS code signature and
isolated `--version` / `--help` probes passed. See
[the bounded inspection receipt](desktop-runtime-inspection.json).

The absence of `claude` on PATH did **not** mean no CC runtime was installed.
This executable is managed by Desktop, and its internal versioned path can
change during Desktop updates. Its discovery is historical evidence, not an
independent mise-managed CLI installation or qualified workspace binding.
Subscription login, DeepSeek inference, session handoff and MCP were not tested.

The selected direction is independent CC and Codex CLIs without requiring their
Desktop applications. Do not remove Desktop or migrate its histories as a side
effect of this preparation. Installation and subscription login remain separate
qualification steps on each machine.

## Profiles and billing

| Entry | Harness | Provider and authentication |
| --- | --- | --- |
| Claude subscription | Claude Code | Anthropic, Claude subscription login |
| Codex subscription | Codex | Existing ChatGPT subscription workflow; integration pending |
| DeepSeek API | Claude Code | Official DeepSeek Anthropic endpoint, existing authorized API key |

The two JSON files in `profiles/` are native settings **templates**, not active
settings. Neither creates a profile, logs in, supplies a key, configures MCP,
enforces an account spending limit, or implements automatic fallback.

During the separately qualified launch setup, use different `CLAUDE_CONFIG_DIR`
directories under ignored `state/subscription/` and `state/deepseek/`. Pass their
absolute macOS-visible paths in the launch environment. Do not put this variable
in project settings. Validate native credential storage and file writes on the
OrbStack mount before declaring these profiles isolated and usable.

The subscription launcher must clear inherited API tokens, custom provider/model
variables and alternative-provider switches before selecting the subscription
profile. An empty API key in a template is not proof of subscription billing:
inspect effective authentication after login and check the account's extra-usage
setting before enabling unattended quota-based fallback.

The DeepSeek launcher must inject `ANTHROPIC_AUTH_TOKEN` only into its own process,
from the authorized private credential source. The existing credential reader
uses the `harnessbot` row in repository `.secrets/agents.csv`; it has not been
read, copied, printed or activated in this preparation. Do not place the key in
JSON, shell arguments, workspace-wide environment settings, or a global profile.
Keep all DeepSeek model mappings explicit so a Claude model alias cannot select
an unintended upstream model. Native Claude Desktop/Magpie remains independent.

## Independent installation proposal: macOS CC only

The current Mac is Apple Silicon. Read-only inspection found existing mise
2026.9.3, no `claude` on PATH and no Claude/Codex installation in its mise store.
The Desktop-managed 2.1.308 executable described above exists outside that store.
The Ubuntu Codex installation is separate and unchanged.

- Component: official Claude Code **2.1.310**, macOS ARM64 native CLI.
- Source: [Anthropic release v2.1.310](https://github.com/anthropics/claude-code/releases/tag/v2.1.310).
- Artifact: `claude-darwin-arm64.tar.gz`.
- SHA256: `cf47d30004ff26e5cfed6004a29ca94e05ad53d6f890ee1be8bb582e8ce2a5b5`.
- Installer: existing `/Users/{{mstack:MAC_USER}}/.local/bin/mise`; no Node installation.
- Declaration: this directory's `mise.toml`, scoped to macOS, exact artifact/hash.
- Installation/cache: existing macOS mise stores under
  `/Users/{{mstack:MAC_USER}}/.local/share/mise/` and `/Users/{{mstack:MAC_USER}}/.cache/mise/`;
  record the exact resolved executable after installation.
- Configuration writes: this one mise trust entry and generated `mise.lock`.
- Ports, containers, volumes, model calls, credentials and app launches: none.
- Existing global tool selections and Codex/Claude Desktop settings: no edits.

The installed mise version's GitHub backend source was checked for
`asset_pattern` and `checksum` support. Installation has not been attempted.
If its native verification rejects the artifact, stop and retain the evidence;
do not disable integrity checks or upgrade mise as an implicit workaround.

After explicit confirmation of this component, run from Ubuntu:

```sh
macctl run /Users/{{mstack:MAC_USER}}/.local/bin/mise trust /home/developer/workspace/mstack/infra/harnesses/claude-code/mise.toml
macctl run /Users/{{mstack:MAC_USER}}/.local/bin/mise --cd /home/developer/workspace/mstack/infra/harnesses/claude-code install github:anthropics/claude-code@2.1.310
```

`macctl` translates the repository argument to the host-visible path. These
commands do not install or configure Ubuntu tools. Inspect the exact resolved
binary without auto-installing:

```sh
macctl run /Users/{{mstack:MAC_USER}}/.local/bin/mise --cd /home/developer/workspace/mstack/infra/harnesses/claude-code which claude
```

Then verify the returned absolute binary with macOS `codesign --verify --strict`,
record its SHA256, and run only `--version` with auto-updates and nonessential
traffic disabled. Run that probe from a fresh temporary directory with a
temporary `CLAUDE_CONFIG_DIR`. Do not run `doctor`, `auth login`, the interactive
CLI, or a prompt as an installation check. Record the generated lockfile and
effective artifact/hash in ignored evidence before qualifying the installation.

Rollback of a fresh, idle installation is scoped to this exact tool/version:

```sh
macctl run /Users/{{mstack:MAC_USER}}/.local/bin/mise uninstall github:anthropics/claude-code@2.1.310
macctl run /Users/{{mstack:MAC_USER}}/.local/bin/mise untrust /home/developer/workspace/mstack/infra/harnesses/claude-code/mise.toml
```

Run rollback only after confirming no session uses the installed binary. Preserve
any subsequently created credentials/history; do not prune shared caches or
other tool versions. These rollback commands have not been executed.

## Subsequent qualification

Subscription login, profile launchers, workspace provider selection, agent handoff
and project MCP bindings are subsequent steps. Validate the chosen workspace on
Mac and orb-devbox with implementation, independent review and test results before
claiming an integrated workflow. No foreground window is authorized by this
installation proposal.

Sources: [Claude configuration directories and authentication environment](https://code.claude.com/docs/en/env-vars),
[Claude installation and integrity](https://code.claude.com/docs/en/setup),
[DeepSeek's Claude Code integration](https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code/),
[mise GitHub backend](https://mise.jdx.dev/dev-tools/backends/github.html).
