> Retired on 2026-10-15 at the user’s request. This is historical evidence; do not execute setup commands. See [retirement record](../infra/maintenance/mail-retirement/README.md).

# Inbox Zero first login

The local app is running at macOS `http://localhost:58085/login`, but its
foundation installation did not configure provider authentication. There is
no initial administrator password or saved login code.

**October 12 update:** the user supplied Google's downloaded Web-client JSON in
`.secrets/zero-index/`. Its credentials are imported privately and the user has
completed Google sign-in; read-only checks confirm one user and one connected
Gmail account with stored access/refresh tokens. The initial bulk-unsubscribe
scan recovered after Gmail rate limiting; onboarding completion is unconfirmed.
**October 14 update:** Microsoft application **Inbox Zero Personal** is registered
in the now-accessible Default Directory. Personal/organizational account support,
both Web callbacks and seven delegated scopes are configured; the privately saved
client credential is imported and verified. Its secret expires **2027-04-12**.
The existing Gmail owner's **Accounts → Add Microsoft** flow is complete for the
user's intended Hotmail. The user then requested adding their separate Outlook
too; after a transient OAuth failure, a fresh linking flow succeeded. Final UI
and read-only DB checks confirm one user with Gmail, Hotmail and Outlook, all
with access/refresh tokens. Both Microsoft mailboxes reuse the same Entra app.
DeepSeek Flash is configured through
the existing OpenCodex proxy for all AI roles. Synthetic structured JSON,
streaming and tool round-trip checks passed. See the
[AI configuration](../infra/inbox-zero/README.md#deepseek-ai-configuration--2026-10-13).

**Who does what:** the user created the Google client. At the user's request,
the agent created/configured the Microsoft client through the authenticated Edge
window and imported its credential privately. The user completes mailbox sign-in
and consent in the browser. The Microsoft client serves both Outlook and Hotmail;
use **Accounts → Add Microsoft** for each distinct mailbox, within the existing
Gmail-owned Inbox Zero session.

## Why the email-code screen does not send a code

In the installed upstream revision
`0ae922dfd758f89e66aaa14272e6b88d3120bcce`, email-code login cannot create an
account. It requires an existing user with **email sign-in enabled in Settings**.
The code is sent to that user's email address, expires after five minutes and
allows five attempts. Requests for an unknown or disabled account still return
success to avoid revealing which accounts exist.

At initial setup the instance had zero users, Google credentials were `skipped`,
Microsoft credentials were empty, and Resend delivery was not configured. The code screen
therefore cannot bootstrap the owner account. Reading container logs or looking
for a password file will not supply a first-login code.

Source: upstream `apps/web/utils/auth/email-otp.ts`,
`apps/web/utils/auth/email-otp-setting.ts`, and
`packages/transactional-email/src/delivery.ts` in the pinned checkout.

## First login through a mailbox provider

The user selected **Google/Gmail** for first login, then requested **Outlook and
Hotmail** as additional mailboxes. The Google client is now configured;
the Microsoft client is configured and both requested Microsoft mailboxes are connected.
Gmail has created the first account. Link Microsoft mailboxes inside
that account so they are available to the same Inbox Zero user.

For another provider, configure its OAuth
application using the official [Google setup](https://docs.getinboxzero.com/hosting/google-oauth)
or [Microsoft setup](https://docs.getinboxzero.com/hosting/microsoft-oauth).
Use the actual local origin and port rather than the guides' example port 3000;
the registered callback origin must exactly match the app's configured base URL.
Qualify the chosen local origin with the provider before changing the app
configuration.

Keep client credentials in the existing ignored
`infra/inbox-zero/.secrets/runtime.env` with mode 0600. Google uses
`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`; Microsoft uses
`MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, and the prepared
`MICROSOFT_TENANT_ID=common` for the requested personal Microsoft accounts.
Preserve the existing auth/encryption/database secrets.
Never paste a client secret into a public report or store it in committed files.

Once the provider application and callback are qualified, recreate only
`inbox-zero-web` using its existing explicit Compose/env/project arguments.
Sign in using the provider button and complete its consent flow. This creates
the first user through the supported login path. This instance already has its
Gmail owner and connected Hotmail/Outlook; use Accounts for additional mailbox linking.
Check the identity shown on Microsoft's consent page before accepting, because
the app's add flow requests consent without forcing an account picker. The Azure
application owner's sign-in does not select the mailbox for Inbox Zero.

## Optional email-code login afterward

The installed revision delivers transactional login emails through **Resend**.
Configure its API key and verified sender privately, then sign in with the
connected provider and enable email-code access in Settings. Subsequent code
requests arrive in that account's inbox. Email-code sessions cannot manage
authentication settings; use the connected provider for those changes.

An LLM API key is separate from login. Google push notifications also need the
separate Pub/Sub setup and an appropriately reachable webhook. Neither is a
substitute for configuring first-login OAuth.

## Gmail settings for this instance

Use [Google Cloud Console](https://console.cloud.google.com/), select your intended
project, enable **Gmail API**, and configure Google Auth Platform branding and
audience. Personal Gmail needs an External audience with your address added as
a test user. Create a **Web application** OAuth client for Inbox Zero.

Register this JavaScript origin:

```text
http://localhost:58085
```

Register these redirect URIs:

```text
http://localhost:58085/api/auth/callback/google
http://localhost:58085/api/google/linking/callback
```

Google permits HTTP localhost redirects for this local setup;
the origin must match exactly. See [Google's redirect validation rules](https://developers.google.com/identity/protocols/oauth2/web-server#uri-validation).
Calendar and Drive callbacks/scopes are optional and are not required for the
chosen initial Gmail setup.

In Data Access, configure the core scopes specified by Inbox Zero:

```text
https://www.googleapis.com/auth/userinfo.profile
https://www.googleapis.com/auth/userinfo.email
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/gmail.settings.basic
```

This setup and the required Gmail API follow the official
[Inbox Zero Google OAuth instructions](https://docs.getinboxzero.com/hosting/google-oauth).
Keep the client secret private. Replace only `GOOGLE_CLIENT_ID` and
`GOOGLE_CLIENT_SECRET` in
`/home/developer/workspace/mcp-stack/infra/inbox-zero/.secrets/runtime.env`,
preserving all other entries and mode 0600, then notify the agent that the
credentials are ready. The agent can validate without printing them and recreate
only `inbox-zero-web` before you use Google's sign-in button.

OAuth first login and real-time mail processing are separate. With the current
placeholder topic and no Pub/Sub verification token, background Gmail watch
registration cannot succeed; the pinned source logs that background failure
separately from sign-in. Complete the official
[Pub/Sub setup](https://docs.getinboxzero.com/hosting/google-pubsub) before enabling
automatic incoming-mail processing. A public HTTPS webhook/tunnel has not been
configured by this local foundation.

## Outlook and Hotmail settings

The installed provider factory (`apps/web/utils/email/provider.ts`) supports Gmail
API and Microsoft Graph, with no generic IMAP/SMTP mailbox connector. Outlook.com
also requires OAuth2 for IMAP/SMTP; a custom client still needs an Entra app
registration. See [Microsoft's Outlook settings](https://support.microsoft.com/en-us/outlook/pop-imap-and-smtp-settings-for-outlook-com)
and [protocol OAuth registration](https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth).

If portal sign-in shows `AADSTS900561` (GET received where POST is required),
start a fresh private browser session at `https://portal.azure.com/` and complete
sign-in from there. Do not reuse the failed auth URL or navigate Back during
the attempt. The code alone does not establish a tenant or password problem;
report the next page/error before changing settings. See
[Microsoft's error reference](https://learn.microsoft.com/en-us/entra/identity-platform/reference-error-codes).

Outlook.com and Hotmail use the same Microsoft OAuth client. In
[Microsoft Entra app registrations](https://portal.azure.com/), create a Web
application with support for **personal Microsoft accounts plus organizational
accounts** (`signInAudience=AzureADandPersonalMicrosoftAccount`). An organization-only
registration cannot sign in the requested personal Hotmail/Outlook.com accounts.
See [Microsoft's account-audience guidance](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app).

Register these Web redirect URIs:

```text
http://localhost:58085/api/auth/callback/microsoft
http://localhost:58085/api/outlook/linking/callback
```

The local origin is deliberately shared with Gmail. Microsoft's portal accepts
HTTP localhost redirects directly; HTTP `127.0.0.1` registration instead requires
a manifest edit. See [Microsoft's redirect rules](https://learn.microsoft.com/en-us/entra/identity-platform/reply-url).

Create a client secret and privately save its **value**, together with the
application/client ID, in the existing runtime env:

```dotenv
MICROSOFT_CLIENT_ID=YOUR_APPLICATION_CLIENT_ID
MICROSOFT_CLIENT_SECRET=YOUR_CLIENT_SECRET_VALUE
MICROSOFT_TENANT_ID=common
```

Do not replace other settings. The source already defaults to the `common`
authority; it is now explicit in the private env/example. Configure Microsoft
Graph delegated permissions for the current mail-only scope set:

```text
openid
profile
email
User.Read
offline_access
Mail.ReadWrite
MailboxSettings.ReadWrite
```

This list follows the pinned `apps/web/utils/outlook/scopes.ts` with sending and
contacts disabled in the local deployment. The broader official
[Inbox Zero Microsoft guide](https://docs.getinboxzero.com/hosting/microsoft-oauth)
also lists optional sending/calendar/Drive features; those are not enabled here.
`Mail.Send` is required if sending is later enabled; calendar and contact scopes
are added only for their corresponding features.

After the credentials are saved and only the web container is recreated, sign
in with Gmail and use the app's **Add account** flow to connect each distinct
Microsoft mailbox. No Microsoft account has been linked
yet, and no stored authentication was bypassed.
