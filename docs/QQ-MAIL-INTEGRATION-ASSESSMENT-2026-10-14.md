# QQ mailbox integration assessment

Date: 2026-10-14, Asia/Shanghai. Scope: cost/requirements assessment only.
No package, service, mailbox credential, provider call, or harness registration
was installed/configured as part of this assessment. Existing Gmail, Hotmail,
Outlook, Inbox Zero and DeepSeek remain unchanged.

## Conclusion

QQ can be exposed to the current Codex agent using a small project-local IMAP
reader. Adding QQ as an Inbox Zero mailbox is a separate application change.
An external MCP connector does not make it appear in Inbox Zero's Accounts or
give Inbox Zero's embedded DeepSeek assistant access to it.

Recommend starting with on-demand Agent reading if that satisfies the immediate
need. Keep an Inbox Zero adapter as an independently scoped option.

## Evidence and effort estimate

Inspected local Inbox Zero source at
`0ae922dfd758f89e66aaa14272e6b88d3120bcce`:

- `apps/web/utils/email/types.ts`: EmailProvider declares 97 methods, covering
  reading, threads, drafts, folder/label changes, filters, synchronization and
  watchers. A limited adapter need not implement every capability; unsupported
  capabilities must be disabled consistently in both UI and backend.
- `apps/web/utils/email/provider.ts` and `rate-limit-mode-error.ts`: only Google
  and Microsoft are accepted by provider construction/health/rate-limit paths.
- `apps/web/utils/auth.ts`: mailbox linking/profile handling recognizes only
  Google and Microsoft. Retain the existing Gmail owner; add a separate mailbox
  credential flow rather than attempting to use QQ as an OAuth login provider.
- `apps/web/app/(app)/accounts/AddAccount.tsx`: only two provider buttons exist.
- `apps/web/utils/webhook/process-history.ts`: history processing is tied to
  Google/Microsoft. QQ requires a capability-tested IMAP synchronization path.

These are rough engineering person-day estimates based on source inspection,
not elapsed-time promises or a fixed quote. Assumptions: one personal QQ mailbox,
one owner, account login succeeds, no mobile clients or general IMAP product,
and existing Google/Microsoft behavior must keep working. No live QQ capability
or performance test has been performed; a connector spike should refine estimates.

| Deliverable | Estimated effort | Boundaries |
| --- | --- | --- |
| Agent on-demand read-only reader | 0.5–2 person-days | Login, headers/date/sender search, selected message text, bounded output, credential handling and verification; no background sync or send |
| Inbox Zero limited read-only mailbox | 5–10 person-days | Account entry/credential flow, listing/search/read, selected-message AI summary; capability guards, custom build and regression checks; advanced features disabled |
| Inbox Zero maintained read/write integration | 15–30 person-days initially | Draft/send, flags/folders, incremental sync, reconnect/retry, deduplication, AI workflow integration and regression coverage; ongoing maintenance additional |

The full option cannot promise Google/Graph feature parity. Provider-side rules,
label semantics, conversation grouping and event delivery have different protocol
capabilities. UID/UIDVALIDITY, mailbox moves and Message-ID/References must be
handled explicitly. A custom app image must be built and pinned; later upstream
updates require adapter regression checks. Container builds can preserve the
existing VM-config/macOS-Docker split without new host Node installs.

## Minimal Agent path

Here Agent means the current Codex project session. Reuse the already present
Ubuntu Python 3.14.4 and standard-library `imaplib`, `ssl` and `email`; imports
were verified. No Ubuntu mise configuration, package installation, exposed port,
new database or always-on service is necessary for this initial CLI approach.

Proposed files if implementation is requested:

- `integrations/qq-mail/`: reader and focused protocol/credential tests.
- `infra/qq-mail/`: non-secret account settings and project invocation guidance.
- `infra/qq-mail/.secrets/account.json`: QQ address and authorization code,
  ignored, file 0600 and parent directory 0700. This file does not yet exist.

Connect only to `imap.qq.com:993`, explicitly use
`ssl.create_default_context()` for certificate/hostname verification, and bound
timeouts and message sizes. Use EXAMINE/read-only selection and BODY.PEEK so
inspection does not mark mail read. Expose a fixed read operation allowlist;
no STORE, MOVE, COPY, APPEND, EXPUNGE, SMTP or arbitrary protocol command.
Use stable UID plus mailbox/UIDVALIDITY references. Treat message bodies as
untrusted data, never instructions to the agent. Start with headers and fetch
only messages the user requests, rather than downloading a whole mailbox.

The QQ authorization code may allow broader account operations than this reader.
The proposed read-only boundary is enforced by the reader; it is not a claim
that Tencent issues a read-only credential.

Verification sequence: authenticate and inspect mailbox counts; test selected
header retrieval; verify reading an explicitly chosen message leaves its unread
flag unchanged. Mock tests cover mutation-command rejection, credential redaction,
TLS verification, UID selection and bounded reads. No test email or mail mutation
is needed. Rollback removes only this project's reader/config and revokes its
QQ authorization code through the user's mailbox settings.

Codex can invoke the project reader through its existing execution tool. Native
MCP tool registration and access from other agents would be separate follow-up
configuration; no global harness settings or gateway changes are included.
Inbox Zero's DeepSeek settings do not automatically apply to this separate path.

## User prerequisites

1. The QQ mailbox address.
2. Enable IMAP/SMTP in QQ Mail's account settings and generate its client
   authorization code (not the QQ login password); complete Tencent's requested
   identity verification in its UI.
3. Store that code locally in the private file when the configuration template
   is prepared; do not send it in chat.

No Entra or Google Cloud application is required for this QQ IMAP path. The VM
must be able to reach QQ's TLS endpoint; this is not yet qualified. Sending would
be a separately scoped SMTP addition. The initial reader adds no model API cost
by itself; summarization uses whichever agent/model receives the selected text.

## Existing connector research

TimeCyber/email-mcp documents QQ IMAP access, but the inspected `main/index.js`
sets `tlsOptions: { rejectUnauthorized: false }` in both IMAP connection paths.
Do not adopt it unchanged. Its default tool set also includes sending and dynamic
server/credential configuration, broader than the proposed reader.
STARDUSTLC666/dsh-email is a DSH plugin candidate, not a Codex binding; it remains
uninstalled and unqualified. Neither README is evidence of local compatibility.

References:

- [Tencent QQ IMAP/SMTP authorization-code setup](https://hiflow.tencent.com/docs/applications/qq-mail/)
- [Python IMAP support](https://docs.python.org/3/library/imaplib.html)
- [TimeCyber connector source](https://github.com/TimeCyber/email-mcp/blob/main/index.js)
- [DSH email plugin](https://github.com/STARDUSTLC666/dsh-email)
