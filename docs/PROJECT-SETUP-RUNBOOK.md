# Start a real project

Create the project outside the mstack infrastructure repository:

```sh
/home/developer/workspace/mstack/mstack init /path/to/my-project
/home/developer/workspace/mstack/mstack plan --project /path/to/my-project
/home/developer/workspace/mstack/mstack doctor --project /path/to/my-project
```

The only editable mstack config is `.mstack/stack.json`. The one-field default
`{"project":"my-project"}` selects daily. `.mstack/state.json` stores generated
records; `.mstack/secrets/` stores private project credentials. Do not copy demo projects,
old registry files or another project's grants. The examples are retired.

Start with the concrete task. Codex/Claude performs interactive work; Anytype holds
useful project documents; Windmill runs reviewed repeatable jobs. Headroom,
Graphify, Serena and gstack are supporting capabilities used when useful.
CodeGraph remains ignored; OrbStack and mise remain protected system tools.

For each needed capability, reuse an actual harness binding or register a project
tenant in the shared container. See [tenant onboarding](../infra/services/README.md).
Graphify requires an explicitly approved index. Anytype needs the project's own
channel-only key. Windmill needs its own workspace and restricted script tokens.
Neither init nor selecting a preset creates grants, indexes, schedules or services.

After real scoped calls and rejection/readback checks, record qualification in
generated state. `doctor` checks local consistency. `run --inspect` checks the
Codex invocation without inference; `run` launches it with project-only settings.
Native harness adapter files need normal project trust. Existing chats do not
hot-reload tools from mstack files. Claude sessions require separate qualification.

Anytype writes are read back. No automatic memory mirror follows. Use background
APIs/containers/headless browsing while the user uses the Mac; arrange a quiet
window only for native onboarding that requires UI control.

The [configuration guide](MSTACK-CONFIG.md) describes all fields and generated
sections. Historical qualification receipts are evidence of past checks, not
live health or permission to reuse the deleted examples.
