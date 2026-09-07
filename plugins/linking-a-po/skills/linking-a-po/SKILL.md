---
name: linking-a-po
description: >
  Link a Purchase Order that was created manually in D-One's Odoo (not auto-generated from a
  quote) to its originating Sales Order/quote, so it shows up alongside the other POs generated
  from that quote. Use this whenever someone says "link this PO to quote X", "link [PO number] to
  [quote number]", mentions a stray or orphaned PO that should show under a quote, or pastes a PO
  row and asks to link it to a quote. The automation that normally links a newly-generated PO to
  its quote does not run for manually-created POs, which is exactly the gap this skill closes.
---

# Linking a PO (Odoo)

D-One's Odoo normally auto-generates Purchase Orders from a Sales Order/quote (via the Quote
Builder / procurement flow), and the automation links each generated PO back to that quote. When
someone creates a PO **manually** for a project that already has a quote — e.g. an extra item
needed after the fact, ordered from a different vendor — that automation does not run. The PO
exists, but nobody browsing the quote will find it, and it does not count toward the quote's
"Purchase" smart button.

This skill is the manual fix: it makes an orphaned PO show up exactly like an auto-generated one,
under the same quote.

## What actually links a PO to a quote

This was determined by directly comparing a correctly auto-linked PO against a manually created
one, field by field, via Odoo's ORM (not by reading documentation — this is specific to D-One's
customized Odoo instance, not standard Odoo behavior). Do not assume the obvious form fields are
the mechanism; verify with the steps below.

- The PO's **Other Info → Tracking** tab has a **Source** field (technical field name `origin`,
  plain text) and a **Project** field (`project_id`). These are descriptive/display fields only.
  Setting them makes the PO **findable by search/filter** (e.g. filter Purchase Orders by Source =
  quote number), matching what the automation would set — but by themselves they do **not**
  create the actual link. A PO can have the correct Source and Project and still be completely
  absent from the quote's linked-PO list.
- The PO must be a **confirmed Purchase Order** (state = `purchase`), not still a draft RFQ. A
  draft RFQ is excluded from the quote's linked list regardless of any other field.
- The real link is a shared **`stock.reference`** record. Both the Sales Order and every PO
  generated from it belong to the same `stock.reference` record — visible as
  `stock_reference_ids` (many2many, stored) on `sale.order`, and `reference_ids` (many2many,
  stored) on `purchase.order`. This is what actually drives the quote's "Purchase N" smart-button
  count, its "Purchase Order generated from <quote>" list, and the PO's own "Sale" smart button.
- A manually created PO gets its own brand-new, PO-named `stock.reference` record (e.g. one named
  "P00288" containing only itself) instead of being attached to the quote's existing one (e.g.
  "Q82", which already lists all the auto-generated POs plus the SO itself). That mismatch is the
  actual root cause of the automation gap.

## Step-by-step fix

1. **Identify the quote's `stock.reference` record.** Note the quote's name (e.g. `Q82`).

2. **Confirm the orphaned PO is a real Purchase Order, not still an RFQ.** Check its state. If
   it's still in RFQ/draft state, it must be confirmed ("Confirm Order") before it can be linked —
   draft RFQs are excluded from the linked list no matter what.

   **Always ask the user for explicit permission before confirming an RFQ.** Confirming is a real
   workflow state change (it locks the PO) and the user may not be ready to commit to that
   vendor/order yet. Do not confirm unilaterally.

3. **Set Source and Project on the PO** (Other Info → Tracking tab) to match the quote: Source =
   the quote's name (e.g. `Q82`), Project = the quote's Project Name. This makes the PO
   consistently findable by filter/search even independent of the deeper link, and matches what
   the automation would have set. If they're already set correctly, this step is a no-op — don't
   assume that means the PO is already linked (see step 4).

4. **Attach the PO to the quote's shared `stock.reference` record.** This is the step that
   actually creates the link. Using Odoo's ORM (e.g. an authenticated JSON-RPC call to
   `/web/dataset/call_kw` from a logged-in browser tab, or a backend script):

   - Read the Sales Order's `stock_reference_ids` to get the shared reference id:
     ```
     sale.order.search_read([["name", "=", quote_name]], ["id", "stock_reference_ids"])
     ```
   - Add that reference id onto the PO's `reference_ids` using an add-link command (this adds
     without removing anything already there):
     ```
     purchase.order.write([po_id], {"reference_ids": [[4, reference_id, false]]})
     ```

5. **Verify — don't skip this.** Confirming Source/Project look right is not proof the PO is
   linked; the only real proof is:
   - Re-read the Sales Order's `purchase_order_count` — it should have incremented by 1.
   - Open the quote and check its "Purchase N" smart button / list — the PO should now appear
     alongside the others.
   - Open the PO itself — it should now show a "Sale 1" smart button that jumps straight back to
     the quote.

## Gotchas

- **Don't stop at step 3 thinking the job is done.** Source and Project can already be perfectly
  correct on an orphaned PO and it will still be invisible to the quote until step 4 is done.
  Always verify via the actual count/smart button (step 5), never by eyeballing the form fields.
- **Never confirm a draft RFQ without asking first.** Confirming and linking are two separate
  actions; only do the confirm step with explicit user permission.
- **Linking many POs at once:** batch the ORM writes (e.g. loop over a list of
  `(po_id, quote_name)` pairs) rather than doing them one at a time by hand.
- This mechanism (`stock.reference`) is specific to D-One's customized Odoo instance — it will not
  generalize to a stock Odoo install without checking whether the same model/fields exist there.
