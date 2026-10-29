# PostgreSQL UI options — analysis only

> User decision2026-10-05: **WhoDB selected** for simple viewing. The pgAdmin
> recommendation below is superseded. See [current selection](WHODB-VIEWER.md).

2026-10-05. No UI installed, database account created, credential read or runtime
changed. Recommendation balances advanced inspection with a small personal stack.

| Option | Strengths | Tradeoff | Fit |
| --- | --- | --- | --- |
| pgAdmin 4 | PostgreSQL-specific object browser, SQL/data editor, query plans, roles, monitoring, backup/restore tools; desktop or browser deployment | Administration-oriented interface has more concepts than a basic table browser | Recommended for this stack; a later local container fits project-scoped deployment |
| DBeaver Community | Free desktop multi-database client, SQL/data editing and database exploration | Broader interface and desktop runtime/driver management; some advanced product features are paid | Best alternative if you want one desktop client for PostgreSQL and other databases |
| Beekeeper Studio | SQL/table browsing with an approachable desktop interface | Check edition-specific features before selection; less focused on PostgreSQL administration than pgAdmin | Prefer when everyday browsing/editing matters more than administration |

Sources checked: [pgAdmin features](https://www.pgadmin.org/features/),
[DBeaver Community](https://dbeaver.io/),
[Beekeeper Studio](https://www.beekeeperstudio.io/).
Usability judgments are recommendations, not results of a local UI benchmark.

## Recommended shape if selected

One pgAdmin container in Compose project `mcp-stack`, definition under
`infra/pgadmin/`, pinned official image, loopback-only UI, persistent UI settings
in its own volume. Its settings storage need not add another PostgreSQL server.
The UI is independent of Windmill and can inspect multiple permitted databases.
Desktop alternatives can connect to the existing macOS loopback PostgreSQL port
55322; Ubuntu loopback is not the macOS endpoint.

Start with explicit read-only database connections for inspection; privileges
must be granted in PostgreSQL, not inferred from the UI or connection name.
Use a separate administrative connection only for deliberate administration.
Application tables can contain secrets and private execution data, so exposing
all schemas through a UI or to an agent is not implicit authorization.
Never attach {{mstack:CLIENT_REPO}} or unrelated databases automatically. Do not use shared
application superuser credentials or edit application-owned tables as integration.

After the user selects a UI, qualify one exact version/image and prepare ports,
volume, authentication, permitted databases, verification and rollback. This
comparison is not a request to install every option or a prepared install approval.
