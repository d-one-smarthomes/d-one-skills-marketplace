---
name: contractor-callout
description: Set up a D-One contractor call-out / service call in Odoo for the person (usually Stafford) - creates and confirms the SERVICE – CALL OUT Sales Order, the task in the client's project and the contractor's Helpdesk ticket (which emails the contractor), then shows the checklist ticked. Also runs the daily "anything missing" check on call-outs for Berna. Use whenever someone says "call-out", "call out", "service call", "send Benji / the contractor to [client]", "log a call-out for [project]", "client has a problem, send someone", or asks to check call-outs for missing tasks, tickets, hours, POs or invoices.
---

# Contractor call-out (D-One)

The written workflow is in `assets/contractor-callout-workflow.pdf` (3 pages). This skill does **steps 1–3 for the person** (Sales Order, task, Helpdesk ticket), so they only have to answer a few questions. Steps 4–7 belong to the contractor and Admin, and the daily check keeps an eye on them.

## Who you are talking to

Usually Stafford. He is great at the technical work and not comfortable on a PC. So:
- Short, plain sentences. No jargon, no field names, no JSON, no code.
- **One question at a time.** Never a list of questions.
- Accept voice-style messages ("call out Smith house gate intercom dead send Benji").
- Do the Odoo work yourself. Never tell him to click something you can do.
- If something goes wrong, say it simply and say who to ask (Amanda or Berna).

## 1. Log in to Odoo as the person (every chat)

The script runs as whoever is using it, with their own Odoo login and API key, passed only as environment variables:

```bash
export ODOO_USER='<their Odoo login>' ODOO_API_KEY='<their API key>'
```

Find them in this order: already in the environment, in the person's saved Claude preferences, or earlier in this chat. If none, ask for both in one short message, and explain: in Odoo, click your picture (top right) → **My Profile / Preferences** → **Account Security** → **New API Key**, name it "Claude", copy the key. Suggest they save the login and key in their Claude preferences so they never have to do it again.

Rules: use a person's own key only. Never write a key into this skill, a file, a task or a reply. If login fails, say "Odoo didn't accept that login or key" and ask them to check with Amanda.

Get today's date from the system clock (Africa/Johannesburg), never from earlier in the chat.

Script: `scripts/callout.py` (in this skill's folder). Run it with `python3`.

## 2. Set up a call-out (steps 1–3)

### Gather – one question at a time, only what's missing

1. **Which project?** This is the most important answer. **No project, no call-out.** Run `python3 scripts/callout.py find-project "<words>"` with whatever he said (house name, street, client surname). Pick the client's own project (never "General", "Customer Care" or a contractor's project). The customer is taken from the project, so don't ask for the client separately; just confirm the customer shown is right. If more than one project could fit, ask him to choose using plain names ("Buchu House or Buchu Berkley?"). If no project exists, stop and ask Amanda or Berna to create it. Don't create the SO without it.
2. **What's the problem?** Turn it into a short title, 3–6 words, e.g. "Gate intercom offline". This goes in the SO reference, the task and the ticket.
3. **What must the contractor do, and any access notes?** e.g. when the client is home, gate code, who to call. Write it up as a clear description the contractor can follow. If he already said enough, don't ask again.
4. **Which contractor?** Run `python3 scripts/callout.py contractors` to list the Helpdesk teams and their people (e.g. "Synclever(Benji)" → Eisgaaq Benjamin). If there's only one sensible choice, suggest it and let him confirm. Do not use "D-One Support" for a contractor job; that team is for D-One's own staff.
5. **Hours:** don't ask. Use **1 hour**. Admin updates it once the contractor logs the real time. Only use another number if he says so.

### Confirm before creating

Write the plan to a JSON file in the scratchpad:

```json
{"project_id": 0, "partner_id": 0, "problem": "Gate intercom offline",
 "description": "What to check and do...\nClient home after 10:00.",
 "team_id": 0, "contractor_user_id": 0, "hours": 1}
```

`project_id` is required; the script refuses without it and fills `partner_id` from the project if left out. Run `python3 scripts/callout.py create plan.json --dry-run` and show him a short summary in plain words:

> **Project:** Smith House (client: Smith Family)
> **Problem:** Gate intercom offline
> **Contractor:** Benji (Synclever)
> **What they'll do:** Check power at gate, reboot, test call to kitchen panel. Client home after 10:00.
>
> Shall I create it?

Only when he says yes, run `python3 scripts/callout.py create plan.json`.

### What the script does

- **Sales Order**: customer, project, Customer Reference `SERVICE – CALL OUT – <Project> – <Problem>`, one line `[PL] Professional Labour` × hours, then **confirms** it.
- **Task** in the client's project: `S#### – Call out – <Problem>`, with the description, linked to the SO line.
- **Helpdesk ticket** in the contractor's team: `S#### – CALL OUT – <Project> – <Problem>`, assigned to the contractor, linked to the SO and project, description copied in. Saving it emails the contractor. It also posts a message to the contractor with `assets/contractor-time-logging-guide.pdf` attached (how to log time and set the ticket to Solved).

### Tell him it's done

Show the checklist, ticked, with the SO number and three links:

> ✅ Done – **S1801**
> ☑ SO confirmed ☑ Reference says SERVICE – CALL OUT ☑ Project set ☑ Task created ☑ Ticket assigned to Benji – he's been emailed
> [Sales Order](link) · [Task](link) · [Ticket](link)

If the result has `notes` (e.g. the guide couldn't attach), mention it in one plain line. If any step failed, say which one and what was already created, so nobody makes a duplicate SO.

### Special cases

- **Needs to go back, or needs parts:** don't create a new SO for a revisit on the same job. The contractor adds a new timesheet line. If parts are needed, Stafford quotes first. Say so simply.
- **No project exists:** ask Amanda or Berna to create the project. Don't create projects.
- **Never** create the ticket in D-One Support for a contractor, use "General" as the project, or skip confirming the SO.

## 3. Daily check for Berna ("anything missing?")

```bash
python3 scripts/callout.py check --since 2026-11-03
```

`--since 2026-11-03` is the day this workflow started; older call-outs were done the old way and would all show as missing. (`--days N` checks the last N days instead.)

For each confirmed call-out SO (Customer Reference contains "call out") it flags:
- **No project on the SO** (list these first, they block everything else)
- No task with the SO number
- No Helpdesk ticket, or a ticket that isn't assigned
- Ticket Solved but no time logged
- SO labour hours don't match the hours logged (Admin to update the SO)
- Work done but no contractor PO with the SO number as its source
- Work done but the client not invoiced yet

Send the result to **Berna (operations@d-one.co.za)** as a short email: one line per SO (SO number, client, what's missing, link). Subject: `Call-outs – items missing – <date>`. **If nothing is missing, send nothing.** When it runs on a schedule, it needs Odoo credentials available without anyone in the chat (e.g. the person's own private Odoo skill). Never put a key in the scheduled task's instructions.
