---
name: d-one-area-summary
description: Build a D-One Area Summary from Odoo - for one project or all of them, read the Materials lines on each project's Stock Movement task, group them by Area (floor) and Room, and show what is not ordered, on order, part received and received, with a "Needs attention" list, as a shareable page the team can open. Use whenever someone asks for an area summary, a stock or materials summary per area or floor, "what's outstanding on [project]", "what still needs ordering", procurement status by room, a stock movement report, or "run through the projects and show stock" - even if they don't say "area summary". Also use for scheduled weekly stock reports. Read-only on Odoo.
---

# D-One Area Summary

Turns the Materials lines on each project's **Stock Movement** task in Odoo into one page per project, grouped **Area → Room → item**, so site and procurement can see at a glance what is still to order or receive.

Works for anyone at D-One with an Odoo login. It only reads from Odoo, so it is safe to run as often as you like. Everything the skill needs is in this folder. It does not depend on other skills.

## 1. Get the person's Odoo access (first step, every chat)

The script runs as whoever is using it, with their own login and API key:

```bash
export ODOO_USER='<their Odoo login email>' ODOO_API_KEY='<their API key>'
```

Where to find them, in order:
1. Already in the environment, or in the person's own saved preferences or earlier in this chat: use them.
2. Otherwise ask for both in one short message, with how to make a key. In Odoo, click your avatar (top right), then **My Profile / Preferences**, then the **Account Security** tab, then **New API Key**. Name it "Claude", choose a duration, confirm the password and copy the key. The key is shown only once.

Rules, because a key opens the company database:
- Use a person's own key only, never a colleague's.
- Never write the key into this skill, a file, the output page, memory or saved preferences, and never repeat it in a reply. Pass it only through the environment for the command.
- When someone pastes a key, tell them in one line that it now sits in this chat's history. They can delete the key in Odoo (the same Account Security tab) whenever they like.
- If login fails, say "Odoo didn't accept that login or key" and ask them to check both. If d-one.odoo.com can't be reached, the org's network settings need to allow it, so tell them to ask an org owner. Never report numbers from memory.
- If their login can't see purchase orders, the script still runs and notes that PO status wasn't checked. Pass that note on to them.

Always get today's date from the system clock (Africa/Johannesburg), never from earlier in a chat.

## 2. Run it

Run the script from wherever this skill is installed (the folder holding this SKILL.md, often under `/mnt/skills/`). It finds its own template, so you don't need to copy anything first.

```bash
python <skill-dir>/scripts/area_summary.py projects                      # which projects have Stock Movement materials
python <skill-dir>/scripts/area_summary.py build "Gnodde"                # one project
python <skill-dir>/scripts/area_summary.py build --all                   # every project with an open Stock Movement task
python <skill-dir>/scripts/area_summary.py build "House Adler" --all-tasks   # also include goods not on Stock Movement
```

Output goes to `/mnt/user-data/outputs/area_summary.html` (self-contained page, with a project switcher when there are several) and `area_summary.json`. Use `--out` to change the folder. `--include-done` adds projects whose Stock Movement task is marked done.

**Project names.** Every word typed must appear in the project name. If several match (exit code 2, "Buchu" matches nine projects), show the candidates and ask which one. Never pick one yourself.

## 3. Deliver it

1. **Publish the HTML as an artifact** (Artifact tool, `publish`, favicon 📦, title "<Project> area summary"). That link is what the team opens. For a re-run in a later chat, pass the earlier link as `url` so the same page updates instead of creating a new one.
2. In the reply, give a short plain read-out per project: lines and areas, how many not ordered, and the most important attention items (not ordered, do-not-order, PO quantity mismatches, lines missing from Stock Movement). Two to five sentences, not a dump.
3. The published page is private to the person until they share it. Tell them they can share the link with the team from the artifact's share option.
4. **Optional, only when asked:** post a short plain-text version as a note on the project's Stock Movement task (`message_post` on `project.task`, plain text, no HTML). Show the exact text and the task first, and wait for a yes. Don't notify anyone unless the person names who to notify.

## 4. How the data works (and the traps)

Model `x_project_task_material` ("Materials" tab on a task). Fields used: `x_studio_area`, `x_studio_room`, `x_studio_system`, `x_qty_quoted` (Sales Order qty), `x_studio_demand` (Purchase Order qty), `x_studio_received_qty`, `x_studio_po`, `x_studio_supplier`, `x_sale_line_id`.

- **One sales line is copied onto several tasks.** The same line sits on Stock Movement and on Installation, Cabling and Programming Labour and per-room tasks. The script de-duplicates by sales-order line. Never sum Materials across tasks without doing the same, or quantities triple.
- **The Stock Movement copy is the one procurement updates.** Its Received qty is filled; the labour-task copies usually stay at 0. The script prefers the Stock Movement copy.
- **Stock Movement does not hold every item.** On 2026-10-15, Kerzner Estate had 20 goods lines on Stock Movement but 134 on the project overall. Default scope is Stock Movement only (that is what procurement works from), and the missing ones are listed under "Needs attention". Mention that count in the reply; it is often the most useful finding. Use `--all-tasks` if the person wants the full picture.
- **Delivered and Installed are not tracked yet** (7 and 0 lines filled across all of Odoo). The page says so. Do not report anything as "installed" or "on site" from this data.
- **Area spellings vary.** GF/Ground → Ground Floor, FF/First → First Floor, SF → Second Floor, Peremiter → Perimeter. The page notes which raw spellings were merged. Odd values ("CCTV", "Area Group", "0") are kept as they are; blank goes under "No area set".
- **"(Do Not Order)"** typed into the Area or notes is treated as a status, not an area.
- **Status rules:** no live PO or PO qty 0 → Not ordered; PO but nothing received → On order; some received → Part received; received ≥ PO qty → Received. A cancelled PO counts as not ordered and is flagged.
- **Outstanding** = PO qty − received (quoted − received when there is no PO). Cable is in metres, so don't add outstanding quantities up into "units".
- Services (labour, design credit) are excluded.

## 5. Scheduled runs

These only work if the run has Odoo credentials without anyone in the chat, for example a D-One Odoo connector whose key is stored server-side. Without that, say a scheduled run can't log in and offer an on-demand run instead. Never store a key in a scheduled task's instructions.

## 6. Changing the page

`assets/template.html` holds the layout; the script swaps `/*__DATA__*/null` for the JSON. D-One blue `#1379C9`, navy `#0E2A47`; red = not ordered, amber = on order, green = received, grey = do not order. Keep it one self-contained file with light and dark colours.
