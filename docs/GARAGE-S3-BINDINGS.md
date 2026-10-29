# Garage S3 application bindings

2026-10-05, explicitly requested by the user. No service restarts, provider calls,
workflow deployment, credential rotation or new project database.

## n8n: registered

The installed2.41.6 native `s3` credential schema was inspected. Its endpoint
field is `endpoint`, correcting the previously prepared `s3Endpoint` field.
One unique credential was created through the supported `n8n import:credentials`
command, explicitly assigned to the sole existing personal project:

- Name: `mcp-stack-demo / Garage S3`
- Type: generic S3
- Endpoint: `http://mcp-stack-garage:3900`
- Region: `garage`
- Force Path Style: true; Ignore SSL Issues: false
- Key: existing Garage `mcp-stack-demo-n8n` read/write key, entered privately
- Bucket to select in S3 nodes: `project-mcp-stack-demo-artifacts`

Plaintext import was supplied on stdin and held in an exclusive0600 temporary
container file. Native CLI applied normal app encryption/project ownership;
that temporary file was removed in a finally block. Only this new credential's
storage was inspected; its secret was absent from encrypted storage. Existing
credential ID/name/type/update timestamp remain unchanged. No unrelated credential
was read or decrypted; no owner password/token or browser cookies were used.

The first CLI import could not find its input because macctl rewrote the
container path into a macOS path. It created no credential. The corrected call
constructed the in-container arguments inside Node's `spawnSync`, then imported
successfully. Private logs/baseline/target/result are under `infra/garage/state/`.
Do not rerun the import; it is not a synchronization command.

Container-level S3 PUT/GET/list/isolation had passed at Garage installation.
No workflow was needed to register this credential and none was created. The
installed `execute --file` option remains in help but is rejected in source;
testing a native workflow would require separately importing an inactive workflow
and checking CLI runner/broker initialization. Do not claim that test happened.

To use it, select this credential on a generic S3 node and the demo bucket.
The n8n personal project contains the credential; its project-named label is not
an independent application tenant/security boundary.

Rollback, if requested: remove only this unused credential through n8n's supported
UI/API after confirming no workflow references it. Keep the Garage key/bucket/data;
key revocation/volume deletion are separate operations.

## Windmill: awaiting authentication

Read-only inventory found only workspace `admins` (`Admins`). No project API token
is available in repository state. `wmill` is not installed in the worker and no
package was installed for this operation; standard-library HTTP is sufficient.
Read-only inventory also found no installed `s3` resource type. Its schema must
be qualified and, if still absent, registered through Windmill's supported API
as part of the binding after workspace authentication is available.

Using your authenticated account, choose the target workspace and create a token
that can read/create its private resources (and secret variables if you want the
S3 fields kept as secret-variable references). Save it privately as
`.secrets/windmill_api_token`0600 and tell the agent the workspace ID. Do not paste
it into chat, read the owner password or use the built-in default login to bypass
that account. Existing application tokens were not harvested from PostgreSQL.

The private S3 values are prepared at
`infra/garage/state/windmill-resource.private.json`. Proposed resource type `s3`,
within a user/private project path, with bucket/region/endpoint/useSSL/pathStyle
and the existing Windmill-specific read/write key. The resource API uses
`POST /api/w/<workspace>/resources/create` with `path`, `value` and `resource_type`.
First check membership, installed resource schema and absence of the target.
Prefer native secret variables for access/secret key references and verify
interpolation/access before reporting it bound. Do not expose raw keys in a
resource that will be shared broadly with workspace users.

No resource/workspace/user/token was created through direct database writes;
no default owner login was attempted. Approval for this S3 binding remains valid;
missing authenticated input, not another permission request, is the remaining
dependency.

[Message/data flow and centralized model credentials](MESSAGE-AND-DATA-FLOW.md).
