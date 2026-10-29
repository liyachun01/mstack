# Notion → Anytype: kase

Completed on 2026-10-09. Linguist, Thing Logs, and Content Base are together in the new personal channel **kase**. One channel retains their shared database rows, relations and page links. Notion was read through the existing authenticated `ntn` CLI and was not edited.

Open **kase** in Anytype and use the sidebar entries **Linguist**, **Thing Logs**, and **Content Base**. The **kase** landing page also links to **Original files**, containing original attachments, a source-structure archive and **Formula definitions**.

## What moved

| Source | Destination |
| --- | --- |
| 567 pages, including Archived Docs and its descendants | 567 native Page objects |
| 44 database containers with 42 distinct data sources | 42 shared native collections |
| 451 database rows | 451 verified collection memberships |
| 9,308 source blocks, including table rows | 8,295 document blocks; table cells remain inside native tables |
| 50 saved views | 50 collection views and 48 corresponding embedded view instances |
| 43 inline databases | 43 embedded collection blocks |
| 154 relation targets and 52 internal text links | Native Anytype object references |
| 121 available attachment URLs | 117 file objects after content deduplication; all originals backed up |

Nested page links, rows/columns, lists, checkboxes, simple tables, rich text, code, media, saved filters, sorting and field visibility were transformed explicitly. Collection and embedded view column order was restored. New rows use the built-in Page type.

## Collection organization cleanup — 2026-10-09

At the user's request, the 42 custom types created during migration were removed
from the Types panel by archiving them in Bin. All 451 imported database rows now
use the existing Page type. The 42 databases remain native Collection objects
under the built-in **Collections** entry. Their original embedded positions,
properties, membership, filters, sorting and cross-links remain intact.
All 98 collection and embedded view instances across 62 owning objects now
create Page rows, so they no longer depend on the archived types.

Before cleanup, all 612 pages/collections (including the three navigation pages)
and all 42 owned type definitions were backed up privately. Every changed object
was read back, followed by a full comparison of all 612 objects with that backup:
**zero unexpected differences**, zero live migration-created types and zero rows
assigned to those types. All 42 collections remained discoverable. Object IDs and
property definitions were preserved; the only intended changes were row types
and view defaults. The retired types can be restored from Bin; private backups
retain their definitions and each row's prior type assignment.

Cleanup evidence is under `organization-cleanup/` in the private migration state.
`notion_organize.py` performs bounded cleanup through the existing kase-only
binding. Type archival is restricted to the exact migration-owned type keys,
with conditional writes; ordinary transfer clients continue to reject deletion.
Seven focused offline checks passed, including that archival scope guard.

## Verification

All **609 migrated page/collection objects** were read back from Anytype. Their properties, references, document hierarchy, table cells, collection membership and saved-view settings match the transformation, with **zero unresolved differences**. The comparison accounts for equivalent Markdown escaping and omitted trailing empty cells. Six focused offline checks passed, including large nested pages, cyclic references and formatted-span handling.

Available files were downloaded into a protected backup, uploaded and downloaded from Anytype for verification. Anytype re-encoded 19 images; image dimensions and appearance passed comparison. The six ZIP archives inside **Original files** contain untouched original bytes and raw source structure; each uploaded archive was verified by SHA-256. Readback evidence and manifests are in the ignored private state directory.

The desktop rendered checks covered the landing page, Content Base/Archived Docs entry, Linguist inline collections, and Thing Logs with statuses and linked things.

## Differences from Notion

- One formula's results across 18 rows are snapshots. Its original expression is readable under **Original files → Formula definitions**; it is not a live calculation.
- Six timeline views become calendars using their original start Date fields and available end fields. Timeline zoom and manual group/card ordering are not reproduced.
- Column grouping is retained, but exact fractional width ratios and Notion named icons are not portable through the installed API.
- Date ranges use separate start/end properties. Seven populated people fields retain names as text instead of creating Anytype members.
- Thirty-five formatted or linked text properties retain their cell text, with the rich version also rendered inside the corresponding row page.
- Six unavailable or empty source blocks retain links to their exact originals. Three are legacy attachment aliases, one is an opaque page link, and two have empty URLs. Their unavailable contents could not be recovered through the authenticated API or Markdown fallback.

| Unavailable/empty source item | Recovery link |
| --- | --- |
| attachment | [Original block](https://www.notion.so/38699dcef4998009a987f451de45cf90#38699dcef49980d49b4dcbf2ee80b026) |
| link_to_page | [Original block](https://www.notion.so/2f799dcef49981ad81b0e90e883888f2#2f799dcef499816caafded4a35057385) |
| preview | [Original block](https://www.notion.so/2f799dcef49981b38271f098d11d9064#2f799dcef4998141a2a4c62b955aefee) |
| alias | [Original block](https://www.notion.so/2f06543ec1c34279b59e7419431eb4e3#cd0d77b794df4f88b514db38572f2c7b) |
| alias | [Original block](https://www.notion.so/5f889b2e84d141dbb6fbae7d44e65b13#d5afb8dc07494396bf8a87043d957339) |
| alias | [Original block](https://www.notion.so/6b768dbd3e1d4dd8aadf85d0e50ccdd1#1d63d0e09033403fa10abdf6273c39a9) |

This is a one-time transfer. The source archives retain the source definitions and unsupported presentation metadata for later reconstruction.

## Scope and records

The dedicated channel-only credential is referenced by `infra/migrations/notion-to-anytype/config.json`; its value is not in this report or source files. The authenticated grant was checked and a foreign-space read was refused with `403 space_not_granted`. Root Anytype remains unbound, Clock access was not reused, and no global MCP registration or service setup was performed.

Private state: `infra/migrations/notion-to-anytype/state/kase-2026-10-09/`. `ledger.json` records destination identities and write checkpoints; `snapshot.json` is the raw source; `transform.json` is the initial frozen plan; `corrected-transform.json` and `final-readbacks/` retain the original migration verification. `organized-transform.json` and `organization-cleanup/verified/` record the subsequent type cleanup. Preserve this directory and the original archives. Scripts are under `integrations/migrations/` and execute destination requests on macOS through `macctl`, with an explicit Space-bound client. Do not rerun the source snapshot or initial migration stages over this completed migration or treat its credential as another project's binding.

Anytype saved; **memory refresh pending** because this migration has no provisioned ai-memory binding. No memory mirror was created.

References: [Notion CLI](https://developers.notion.com/cli/get-started/overview), [Notion API](https://developers.notion.com/reference/intro), [Notion saved views](https://developers.notion.com/reference/list-views), [Anytype v2 document API](https://developers.anytype.io/docs/reference/v2/anytype-api/).
