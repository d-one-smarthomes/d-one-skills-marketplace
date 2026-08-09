---
name: d-one-proposal
description: >
  Generate an interactive, client-facing D-One home technology proposal and publish it as a
  live hosted link. Use this skill whenever someone asks to create a client proposal, send a
  proposal to a client, build a home technology options document, or present system options
  and budgets to a prospective D-One client. Also trigger when someone says "make a proposal
  for [client name]", "create options for [project]", or "put together a brief for a client".
  The output is a branded interactive HTML page hosted on Netlify — the client receives a link,
  selects their preferred option per system (Entry / Mid / Premium / Not Required), and sees a
  live budget estimate per category. A budget summary table at the bottom updates live. No grand
  total is shown — each category (Security, IT, Audio Visual, System Integration) is independent.
---

# D-One Client Proposal Skill

You generate a branded, interactive HTML proposal for a D-One client and publish it live via
Netlify. The client opens a URL, reads about each system, selects their preferences, and sees
a live budget per category. The result gives D-One a clear brief to work from.

---

## Step 1 — Gather the brief

Ask the user for the following. If they've already provided any of these in their message,
don't ask again:

- **Client name** (used in the heading and Netlify URL slug)
- **Project name or address** (e.g. "Constantia residence", "De Klerk house")
- **Project drawings** — uploaded images or PDFs; these go on the cover page
- **Budget numbers** — for each system and tier below (can come from the component counting
  skill, from a quote, or be left as TBD)
- **Any systems to exclude** — if the client has no interest in a particular category, it
  can be hidden entirely
- **Any special notes** to include (e.g. phase 1 only, specific rooms, client preferences)

### Budget input format

For each system, you need up to three numbers (Entry / Mid / Premium). These are shown as
"From R X" or a range "R X – R Y". If a budget is not yet known, use "TBD" and style it
accordingly in the HTML.

Example input format the user might provide:
```
CCTV: Entry R45k, Mid R85k, Premium R150k
Access Control: Entry R30k, Mid R65k, Premium TBD
Network: Entry R55k, Mid R90k, Premium R160k
Audio: Entry R40k, Mid R75k, Premium TBD
Home Theatre: Entry R80k, Mid R180k, Premium TBD
Lighting: Entry R60k, Mid R110k, Premium R220k
System Integration: Entry R35k, Mid R70k, Premium R140k
```

---

## Step 2 — Read the content reference

Read `references/content.md` in full before generating the HTML. This file contains the
approved copy for every system and tier. Use it verbatim — do not rephrase or improvise the
descriptions. The only things that vary per proposal are the client name, project name,
drawings, and budget numbers.

---

## Step 3 — Proposal images (hosted, hot-linked)

Each option card's photo is **hot-linked from a live image host**, not baked into the
skill. The host mirrors D-One's image library at stable URLs:

    <base_url>/<system-slug>/<tier>.jpg
    e.g. https://d-one-proposal-images.netlify.app/cctv/entry.jpg

`base_url` lives in `config/image_host.json`. Because the proposal only references URLs,
**changing a photo never touches this skill** — you replace the source file and re-publish
the host (see "Where proposal images come from" below). If `base_url` is blank, generation
falls back to the bundled base64 images in `assets/images/` (self-contained, offline-safe).

---

## Step 4 — Generate the HTML

Create a single `index.html` file. The page must:

### Cover page
- Full-width display of the project drawing(s) — if multiple, show as a scrollable gallery
- D-One logo top-left
- Client name and project name as the heading
- Prepared by D-One, with contact: darren@d-one.co.za
- A brief intro paragraph: "This document outlines the technology options for your home.
  For each system, choose the level that suits you. There are no right or wrong answers —
  your selections give us what we need to prepare a detailed proposal."

### Navigation
- Sticky top nav with the four category names: Security | IT | Audio Visual | System Integration
- Clicking jumps to that section
- Active section highlighted as user scrolls

### Per-category sections
Each of the four categories (Security, IT, Audio Visual, System Integration) gets its own
section with:
- Category heading
- The systems within it, each as a card row
- A **category budget subtotal** that updates live as the client makes selections
- The subtotal is shown prominently at the bottom of each category section

### Per-system cards
Each system has four option cards: Entry, Mid, Premium, and a system-specific "Not Required" card.
The cards must:
- Show the tier name (Entry / Mid / Premium) as the card heading
- Show the approved description text from `references/content.md`
- Show the budget for that tier (or "TBD" if not provided)
- Show the relevant photo if available
- Be selectable — clicking a card highlights it and deselects the others (3px gold border + glow on hover/selected)
- Only one card can be selected per system at a time
- The 4th "Not Required" card uses a system-specific label (e.g. "We don't need CCTV") and is displayed narrower (0.35fr) than the three tier cards
- "Not Required" contributes nothing to the budget total
- A radio-dot indicator in the top-right corner of each card fills gold when selected

### Budget display
- Each category section shows: "Your estimated budget for [Category]: R X,XXX,XXX"
- This updates live as the client clicks cards
- TBD budgets contribute 0 to the total but show a note: "* Some items are TBD —
  final budget subject to detailed scope"
- Do NOT show a grand total across all categories

### Design

Match the aesthetic of existing D-One proposals exactly. Reference sites: 1sunset.netlify.app, d1buchu.netlify.app.

**Colour palette:**
```
--dark:    #17140F    (primary dark background)
--dark2:   #211D16    (secondary dark, alternating sections)
--cream:   #F3EDE2    (light sections)
--cream2:  #EAE2D4    (alternate cream)
--gold:    #B8944A    (accent: eyebrows, rules, dividers)
--gold-lt: #D4AE6A    (lighter gold on dark backgrounds)
--stone:   #8C7E6B    (body text on dark)
--white:   #F8F3EB    (text on dark)
--blue:    #1B72BE    (interactive highlights only)
```

**Typography** — import from Google Fonts:
```html
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500&display=swap" rel="stylesheet">
```
- Headings: `Cormorant Garamond`, serif, weight 300–400
- Body: `DM Sans`, sans-serif, weight 300
- Eyebrows: DM Sans, uppercase, letter-spacing 0.2em, gold colour

**Eyebrow → title → rule → body pattern** (use this consistently):
```html
<div class="eyebrow">01 — Security</div>
<div class="title-serif">CCTV</div>
<div class="rule"></div>
<p class="body-text">...</p>
```

**Rules:** 48px wide, 1px tall, gold colour, `margin: 32px 0`
**Full-width rules:** 100% wide, gold at 25% opacity

**Sections alternate** between `.slide-dark` and `.slide-cream` backgrounds.

**Cover page:** Dark background (#17140F), large serif client name, gold rule, cream body text.

**Category sections:** Each category (Security, IT, Audio Visual, System Integration) is a dark-background section with a gold eyebrow. Systems within each category are subsections.

**Option cards (Entry / Mid / Premium / Not Required):**
- Dark card background: `#211D16` with gold border on hover and when selected
- Selected state: gold left border (3px), slightly lighter background
- Card has: eyebrow-style tier label (gold, uppercase), title (serif), body text (stone/cream), budget line (gold)
- "Not Required" card: same style, dimmer, no budget contribution
- Cards in a responsive grid: 2-up on desktop, 1-up on mobile

**Budget display per category:**
- Sits at the bottom of each category section
- Style: `font-family: DM Sans; font-size: 14px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--gold)`
- Format: "ESTIMATED BUDGET — SECURITY: R 450,000"
- Updates live as cards are selected

**Navigation (sticky):**
- Dark background `#17140F`, gold bottom border 1px
- Category links in DM Sans uppercase, letter-spacing, gold on hover/active
- Smooth scroll to sections

**Mobile:** Single-column cards, nav collapses gracefully, touch-friendly tap targets (min 48px)

**No grand total** across all categories — each is independent.

### Footer
- "This proposal was prepared by D-One. For questions, contact darren@d-one.co.za"
- D-One website: www.d-one.co.za
- "Prices are estimates and subject to detailed design and final scope."

---

## Step 5 — Extract Room Names and Collect Plan Paths from Drawings

**Before generating the HTML, read the uploaded floor plan drawings.**

All uploaded floor plans (PDFs or images) serve two purposes:
1. **They become the Project Plans section** — embedded in the proposal so the client can see their marked-up layouts
2. **They provide the room names** — used as the audio zone checkboxes

For each uploaded drawing:
- Note its file path under the uploads directory
- View/read it to extract all labeled room names and outdoor areas
- Collect the absolute file paths in order (Ground floor first, then upper floors)

Compile:
- `ROOM_NAMES` — list of all room labels seen across all plans
- `PLAN_PATHS` — comma-separated absolute paths to all plan image/PDF files

If no drawings are provided, fall back to the default zone list (built into generate.py) and show placeholder plans in the proposal.

**For PDFs:** Convert each page to an image first (use the `pdf` skill or `pdf2image`/`fitz`)
before passing to generate.py, since `--plans` expects image files (PNG/JPG/WEBP).

---

## Step 6 — Generate and Preview (Local Review First)

**Run on the user's Mac** (not the sandbox — the sandbox cannot reach external APIs).
Use `mcp__Control_your_Mac__osascript` with `do shell script`:

```bash
cd '/Users/darrenswanepoel/Library/Application Support/Claude/local-agent-mode-sessions/.../outputs/d-one-proposal'

# Generate with real budgets from the budget-analyzer skill
python3 scripts/generate.py \
  --client "[Client Name]" \
  --project "[Project Name]" \
  --output /Users/darrenswanepoel/Downloads/proposal-[client-slug]/ \
  --budgets-file '/Users/darrenswanepoel/Downloads/budget-analysis/proposal_budgets.json' \
  --plans "/path/to/ground_floor.png,/path/to/first_floor.png" \
  --audio-zones '["Living Room", "Kitchen", "Master Bedroom", "Covered Patio", "Pool Deck"]'
```

**`--budgets-file`** is the output of the budget-analyzer skill (`proposal_budgets.json`). It
contains both the tier card prices (Entry/Mid/Premium for each system) and the per-unit zone
prices (per audio zone, per access control reader). When provided, it fully replaces the demo
numbers — no manual price entry needed.

If no `--budgets-file` is provided, the proposal falls back to demo prices (TBD on some systems).

Any number of plans can be passed — they are all embedded and displayed in the Project Plans
section. The grid adapts: 1 plan = full width, 2 = side by side, 3 = three columns, 4+ = two
columns wrapping.

Then open the file locally for review:

```bash
open -a 'Google Chrome' /Users/darrenswanepoel/Downloads/proposal-[client-slug]/index.html
```

Tell the user the proposal is ready to review locally and ask if they'd like any changes before
publishing. **Do NOT deploy to Netlify at this stage.**

After any revisions, regenerate and reopen. Repeat until the user explicitly says something like
"publish", "deploy", "send to client", or "make it live".

---

## Step 7 — Publish to Netlify (Only When Explicitly Instructed)

**Only run this step when the user explicitly asks to publish, deploy, go live, or send the link
to the client.**

Update `fresh_deploy.py` in Downloads to point to the correct output folder, then run it via
osascript:

```python
# In /Users/darrenswanepoel/Downloads/fresh_deploy.py — update these two lines:
FOLDER = '/Users/darrenswanepoel/Downloads/proposal-[client-slug]/'
SITE_NAME = 'd1-[client-slug]'
```

```applescript
do shell script "nohup python3 /Users/darrenswanepoel/Downloads/fresh_deploy.py > /Users/darrenswanepoel/Downloads/deploy_log.txt 2>&1 &"
```

Then poll the log until "Live at:" appears:
```applescript
do shell script "cat /Users/darrenswanepoel/Downloads/deploy_log.txt"
```

`fresh_deploy.py` uses the Netlify Files API (digest method) and uploads with
`Content-Type: text/html; charset=utf-8` to ensure the page renders correctly.

The site name `d1-[client-slug]` must be unique — if taken, it auto-appends a timestamp.

Share the live URL with the user once confirmed ready.

---

## Step 8 — Deliver

Tell the user:
- The live URL (ready to send via WhatsApp or email)
- A one-line summary of what was included

Example:
> "Proposal for the Smith residence is live: https://d1-smith.netlify.app
> Covers Security, IT, Audio Visual and System Integration — all seven systems included."

---

## Where proposal images come from

**Option photos are hot-linked from a live image host** — the proposal HTML references
URLs, so the images are decoupled from the skill entirely. Change a photo and every
proposal (new *and* already-sent) updates; the skill is never edited or re-packaged.

- **Host:** a dedicated Netlify site, `https://d-one-proposal-images.netlify.app`
  (set in `config/image_host.json` > `base_url`).
- **URL scheme:** `<base_url>/<system-slug>/<tier>.jpg`
  (e.g. `.../lighting/premium.jpg`). System slugs: `cctv`, `access-control`, `network`,
  `audio`, `home-theatre`, `lighting`, `system-integration`. Tiers: `entry|mid|premium`.

### WHERE TO CHANGE THE PHOTOS  ← read this

The single source of truth is the Google Drive folder:

    Claude Cowork / Images / Proposal skill images
    (full path in config/image_host.json > "source_folder")

organised as `<Category>/<System>/<Tier>/` with **exactly one image per Tier folder**
(any format — jpg/png/webp — and any filename). To change a proposal photo:

1. Drop the new image into the right `Category/System/Tier` folder, removing the old one
   (keep one file per folder).
2. Re-publish the host — on a machine that can see the Drive folder and reach Netlify
   (i.e. the Mac): `python3 scripts/publish_images.py`
   (or `--dry-run` to preview the mapping without deploying). This normalises every image
   to `<system-slug>/<tier>.jpg` and pushes the whole folder to the host.

That's it — no skill edit, no re-package, no reinstall. The `Category/System → slug`
mapping lives in `config/image_host.json > slug_map`.

### Resolution order in `generate.py`

1. `DONE_PROPOSAL_IMAGE_BASE_URL` env var, if set.
2. `config/image_host.json` > `base_url` (the default — hot-links the host).
3. If `base_url` is blank/unset → falls back to a baked-in base64 image from the external
   Drive folder (`config/image_source.json`) or the bundled `assets/images/` — the
   self-contained, offline-safe path.

The bundled `assets/images/` set is retained only as that offline fallback; the live host
is the source everyone actually sees.

---

## Notes

- All copy comes from `references/content.md` — keep it up to date as D-One's offering evolves
- The Netlify token is in `config/netlify.json` — do not share the packaged skill file publicly
- Proposal option photos are hot-linked from the live host (`config/image_host.json` >
  `base_url`); the bundled `assets/images/` set is only an offline fallback used when
  `base_url` is blank. See "Where proposal images come from" above
- To change a photo: replace it in the Drive `source_folder` (one image per
  `Category/System/Tier`), then run `python3 scripts/publish_images.py`. No skill edit or
  reinstall needed — see "Where proposal images come from" above
- If the component counting skill has been run on drawings, its output can be passed directly
  as the budget numbers for this skill
- Budgets are shown as estimates, not fixed prices — the footer disclaimer handles this
