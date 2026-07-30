# D-One Skills Marketplace

Private plugin marketplace for D-One's custom Claude skills. Push this repo to a **private** GitHub repository, then connect it as a GitHub-synced marketplace in Claude so the whole team can install these skills.

## Skills included

- **budget-analyzer** — derive per-unit budget averages from supplier/contractor quotes
- **component-schedule** — D-One branded Component & Equipment Schedule PDF
- **conduit-schedule** — D-One branded Conduit Schedule Excel
- **d-one-lead-filter** — qualify a new lead through eight gates to a Pursue / Caution / Decline verdict, with respectful decline drafts
- **d-one-proposal** — interactive client-facing proposal, published as a hosted link
- **d-one-technical-file** — full technical documentation workflow from a WeQuote PDF
- **floorplan-icons** — place D-One AV/tech icons onto a PDF floorplan
- **floorplan-takeoff** — component quantities spreadsheet from an annotated floorplan
- **lighting-takeoff** — lighting item counts from an electrical layout floorplan
- **wequote-budget** — Entry/Mid/Premium budgets for proposals

## 1. Push to GitHub

```bash
cd d-one-skills-marketplace
git init
git add .
git commit -m "Initial D-One skills marketplace"
git branch -M main
git remote add origin https://github.com/<your-org>/d-one-skills-marketplace.git
git push -u origin main
```

Create the GitHub repo first (as **Private**) at github.com/new, then run the commands above from inside this folder.

## 2. Connect it in Claude

Requires a Team or Enterprise plan Owner/Primary Owner, with Cowork and Skills both enabled org-wide.

1. Go to **Organization settings > Plugins** in Claude.
2. Click "Add plugin" and select **GitHub** as the source.
3. Enter the repo as `<your-org>/d-one-skills-marketplace`.
4. If prompted, install the Claude GitHub App on the repository.
5. Once synced, set each plugin's installation preference (Installed by default / Available for install / Required) so the team gets access.

## 3. Updating skills later

Edit the skill files under `plugins/<skill-name>/skills/<skill-name>/`, commit, and push. If "Sync automatically" is enabled for the marketplace, Claude picks up the change on merge to `main`. Otherwise, trigger a manual sync from **Organization settings > Plugins**.
