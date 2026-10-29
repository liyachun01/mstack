# Garage S3 storage

Resumed in place and verified healthy on 2026-10-16 after the user reported it
stopped. The existing container had exited cleanly at 2026-10-11 21:14 UTC; the
inspection does not establish who stopped it or why. Original image, container
identity, credentials and both volumes were preserved. Signed S3 listings with
both retained service keys return 200 from the Windmill worker; anonymous access
returns 403. All 28 other containers are unchanged. No objects or application
bindings were created. See [the resume receipt](resume-20261016.json).

Installed and healthy2026-10-05. See [installation evidence](../../docs/GARAGE-INSTALL-RECORD.md)
and [deployment and service linking](../../docs/GARAGE-SETUP.md).

Recovered and verified 2026-10-09 with its original node, bucket, service keys
and matched metadata/data volumes. Both original keys pass read-only S3 checks.
See [the recovery report](../../docs/SERVICE-RECOVERY-2026-10-09.md).

Use only this overlay's `garage` service in Compose project `mstack`.
Never run project-wide `down`, `--remove-orphans`, or volume cleanup.
The definition connects Garage to the existing Windmill and n8n networks without
recreating either client. Network connectivity is not application registration.

Persistent volumes: `mcp-stack-garage-meta`, `mcp-stack-garage-data`.
Local S3 endpoint on macOS: `http://127.0.0.1:53900`.
Container endpoint: `http://mcp-stack-garage:3900`, region `garage`, path style.
Secrets belong only in ignored `state/` (directory0700, files0600).
Scoped Compose lifecycle commands require `--env-file infra/garage/state/runtime.env`.
Container CLI through macctl is `./garage`; a standalone `/garage` argv is rewritten.
