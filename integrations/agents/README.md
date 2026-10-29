# Project agent bindings

[Integration inventory and per-tool diagrams](../../docs/AGENT-INTEGRATIONS.md).
The plan registry is `infra/agents/integrations.json`; it is not an automatic
installer, policy enforcement engine or harness registration.

`deepseek_launch.py` reads only the selected `harnessbot` row from the private
three-column provider/name/key CSV. Its default mode checks the installed version,
existing profile and project patches, without startup, HTTP or model calls:

```sh
python3 -B integrations/agents/deepseek_launch.py
```

Output contains only aliases, command/config paths and environment variable
names. Never print the returned environment from an imported function.
An approved launch uses `--launch`, after the existing idle Web process's
identity has been verified and it has been gracefully stopped. This helper
refuses an occupied port and never stops any process or installs a profile.
Key lives in child memory/environment, not argv, global settings or a copied
credential store. It retains the existing DeepSeek home/settings/sessions and
keeps the currently qualified graph overlay and vision-disable patch.

This is trusted-code execution; Web/harness tools are not a hostile-code sandbox.
No model request is submitted by the launcher. Subsequent user prompts can incur
provider usage and execute tools according to the selected harness permissions.
