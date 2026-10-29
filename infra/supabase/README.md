# Deferred Supabase option

`config.toml` is retained for a possible future isolated Supabase stack. It is not part of `compose.yaml` and must not be started with the current PostgreSQL setup.

The current runtime uses PostgreSQL + pgvector directly. Supabase CLI `2.118.0` remains installed on macOS from the earlier approved step, but is no longer selected by the root mise config. Its removal has not been requested.

Before enabling this option, plan its additional services and migration, allocate new ports (the Compose database reserves `55322`), and obtain separate approval. Never reuse or change `{{mstack:CLIENT_REPO}}` resources or attach Supabase directly to their data volume.
