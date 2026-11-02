---
name: "odoo"
description: "Read from and write to D-One's Odoo (d-one.odoo.com) from any chat on any device. Trigger whenever Darren wants to work with Odoo in any wording: \"add a task/subtask in Odoo\", \"create a CRM entry / opportunity\", \"what's overdue\", \"assign X to [person]\", \"check the [project] tasks\", \"tag it tech meeting\", \"pull my pipeline / quotes / invoices\", or any read/update of projects, tasks, subtasks, CRM leads, or purchase orders. This is D-One's business system — accuracy and correct dating matter."
---

# Odoo — D-One's business system (read + write from any device)

This skill connects Claude to D-One's Odoo over JSON-RPC so it works from any
chat on any device. It contains **no secrets** — the API key lives in Darren's
encrypted key vault (see "Where the API key lives" below), not in this skill,
not in memory, and not in saved preferences.

## RULE 0 — ALWAYS CHECK THE CURRENT DATE FIRST (non-negotiable)

Before creating or dating ANYTHING in Odoo (tasks, subtasks, CRM, due dates,
notes with dates), Claude MUST get the real current date from the time tool
(`user_time_v0`, the session date, or ask Darren if unavailable). **Never** reuse a "today" from
earlier in the chat, from training data, or from a copied example — those go
stale. Resolve "today / tomorrow / Friday / Monday / this weekend" against the
freshly-fetched current date every time. If no date source is available, ask
Darren for today's date before dating anything.

## RULE 1 — "ADD A TASK" MEANS A SUBTASK, NOT AN ACTIVITY (changed 2026-10-05)

D-One no longer uses Odoo activities (`mail.activity`) for tasks. When Darren (or anyone) says
"add a task", "add a to-do", "remind me to…", "create an action for…" in Odoo, create a
**Subtask**: a `project.task` record with `parent_id` set to the relevant parent task, so it
shows up under Tasks.

- `parent_id` = the parent task (find via search_read on `project.task`; for general admin use task 'Admin' (id 4795) in project 'General' (id 84)).
- `project_id` = same project as the parent.
- `name` = task title; `description` = any notes (HTML ok).
- `user_ids` = `[(6,0,[assignee_uid])]` (Darren = uid 5 unless told otherwise).
- `date_deadline` = 'YYYY-MM-DD HH:MM:SS' (default to today from Rule 0 if none given, and flag it).
- Leave `stage_id` unset so the project's default first stage applies.
- If the right parent task is genuinely unclear, ask Darren which parent task to use — don't guess.
- Only create a `mail.activity` if Darren explicitly asks for an "activity" by name.
- When reading "my open tasks", look at `project.task` (incl. subtasks) first; legacy open activities may still exist.

## Where the API key lives (updated 2026-11-02)

The Odoo API key was rotated and moved into Darren's **encrypted key vault**. Any Odoo key
still shown in saved preferences or older notes is **out of date and revoked** — do not use it.

- **Vault entry name:** `odoo` (file `vault/odoo.age`). Its decrypted contents are three
  lines: `ODOO_URL`, `ODOO_LOGIN`, `ODOO_API_KEY`.
- **Primary location:** the `Keys` folder on Darren's Mac (`~/Keys`), which holds the vault
  tool `keyvault.py`, the vault entries in `vault/`, and the master key `master.agekey`
  (the master key lives only on the Mac and in Darren's password manager).
- **Backup copy of the encrypted entries:** the private GitHub repo `d-one-smarthomes/d-one-secrets`
  (encrypted `vault/*.age` files only — it cannot be decrypted without the master key).
- **Get the key (when the Mac is linked to the session):** use the device shell, in the
  Keys folder, and load it straight into environment variables without printing it:

  ```bash
  cd "$HOME/mnt/Keys"
  eval "$(python3 keyvault.py get odoo | sed 's/^/export /')"
  export ODOO_DB=d-one
  python3 odoo_bridge.py        # prints uid 5 on success (if the bridge file is available)
  ```

  If the output format differs, run `python3 keyvault.py list` and `python3 keyvault.py --help`
  to check usage. Do the lookup and the Odoo call in the same command so the key never
  has to be shown.
- **If the Mac is not reachable** (no linked computer, or `device_bash` fails): do NOT fall back
  to an old key. Tell Darren the vault is unreachable and ask him to link the computer or paste
  the key once for this session only.
- **Never** print, echo, log, or quote the key in chat; never write it to any file in a shared
  or synced location, memory, the skills repo, or the scheduled-task prompt. Never put it in
  a URL. Use pattern/length checks (for example "key present, 40 characters") if you need to
  verify it loaded.
- **Rotating or replacing the key:** Darren creates the new key in Odoo (Account Security) and
  Claude re-encrypts it into the vault with `python3 keyvault.py rotate odoo` (key via stdin
  or `--from FILE`), then commits the updated `vault/odoo.age` to `d-one-secrets`.

## Configuration

- `ODOO_URL`   = `https://d-one.odoo.com`
- `ODOO_DB`    = `d-one`
- `ODOO_LOGIN` = `darren@d-one.co.za`
- `ODOO_KEY` / `ODOO_API_KEY` = from the vault entry `odoo` as described above. (The vault
  entry names it `ODOO_API_KEY`; the bridge reads it as `ODOO_KEY`. Map one to the other.)

Call JSON-RPC directly at `https://d-one.odoo.com/jsonrpc`, or use `odoo_bridge.py` if bundled
next to this file. `odoo_bridge.py` is **read-only by default** (`search_read`). Writes go
through `execute_kw(..., 'create'|'write'|'unlink', ...)` — only do these when Darren asks
to add/change something.

## Core how-to

- **Authenticate:** `_rpc("common","authenticate",[DB,LOGIN,KEY,{}])` → uid 5.
- **Read:** `search_read(model, domain, fields, limit)`.
- **Create/Write/Delete:** `_rpc("object","execute_kw",[DB,uid,KEY,model,method,args])`
  with method `create` / `write` / `unlink`.
- **Many2many writes:** set = `[(6,0,[ids])]`, add = `[(4,id)]`,
  remove = `[(3,id)]`, clear = `[(5,0,0)]`.
- **Legacy activities** (only when explicitly requested) need `res_model_id` (ir.model id) +
  `res_model` + `res_id` and a `date_deadline`. `project.task`'s ir.model id is **622**.

See `reference/routing-and-conventions.md` (if available) for D-One's rules on where things go,
tagging, CRM, and common models/IDs. **Read it before writing.**

## After acting

Confirm in one or two lines what was created/changed, with the record and its
owner/date. Don't paste raw dumps. When a write could be ambiguous (which
project, which person, which record), verify against Odoo first and ask if
genuinely unclear rather than guessing.
