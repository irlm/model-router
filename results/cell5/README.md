# Cell 5: the author's own web store through the Chrome extension (2026-10-30)

The browser-flow family of cell 4 repeated on a real application: the Go store of the user's
author's own Go store (Postgres, server-rendered templates, one
small `app.js`), at commit `24211d9`. 15 flows (14 planted defects plus a clean store), a numbered
10-item checklist, three models at effort low, one trial each (plus the repeat trials below). The
agent is a customer: search, open two products, add them to the cart, change a quantity, read the
estimate, place an order with PayPal, cancel it, check the orders list. Truth comes from a scripted
user (`bench/own_app_flow/oracle.py`) that drives the same store over HTTP. A run is `correct`
only when all 10 items match the scripted user. The store's request log says whether the agent
really did the flow (`drove`: full, partial, none). No judge model.
Receipts: `runs/own_app_flow/`; grades: `grades.json`; tables: `tables.md`.

ROUTING.md v1 said the main thing to test next was whether the families transfer from the
benchmark's toy apps to one of the user's own projects. This cell is that test for the browser family.

## The tasks (`bench/own_app_flow/tasks.json`, made by `make_tasks.py`)

- **App:** the real store binary, built from an exported copy of the source with 14 defects planted
  behind an environment variable (`patch_tree.py`, `defects.patch`). One defect per run. A separate
  Postgres container with its own small deterministic seed (500 products, 3,000 customers, 25,000
  orders); the user's real 324 GB store data is never touched. Every visitor is pinned to one
  customer (US, 7% tax) so prices, tax and shipping are the same for the agent and the scripted user.
- **Defects:** search finds only exact matches; the cart badge counts lines not units; "Add to
  cart" ignores the quantity; the cart shows the cost price; the subtotal skips the last line; tax is
  computed on shipping too; shipping charged over the free limit; Update adds instead of setting;
  Update ignored; the payment method is ignored; the order's tax is doubled; cancel does not
  refund; cancel refunds but leaves the status paid; the orders list starts with the oldest.
- **Checklist (10 items):** home shows "Cart (0)" and the customer; search "olive" finds the product
  at $24.99; add 2 of it, "Added to your cart." and "Cart (2)"; add 1 of a second product, "Cart
  (3)"; the two cart rows with price, quantity and line total; the estimate $69.97 + $0.00 shipping +
  $4.90 tax = $74.87; reduce the first product to 1: $44.98 + $5.99 + $3.15 = $54.12 and "Cart
  (2)"; place the order with PayPal: order page "paid", two lines, total $54.12, one payment row
  "paypal" "captured" $54.12; cancel: "cancelled", the refund message, payment "refunded"; the orders
  list starts with that order, "cancelled", $54.12. The flow crosses the free-shipping line on purpose.
- **Truth per defect:** the scripted user's fail set. For example "Add to cart ignores the quantity"
  fails items 3 to 6 (the badge, the rows and the estimate are all off until the Update fixes the
  quantity), "order tax doubled" fails 8 and 10, "cancel does not refund" fails only 9.
- **Each run:** the cart emptied, a fresh store process on its own port with one defect, a fresh
  headless `claude -p --chrome` session with the same tool limits as cell 4 (tab, navigate,
  read_page, get_page_text, find, form_input, computer, browser_batch, resize_window), 90 turns
  max. Sequential: one browser, one Postgres. Orders accumulate in the benchmark database.

## Result (trial 1)

| Model | Correct / 15 | Planted defect flagged / 15 | Flow finished / 15 | Cost per flow (min to max) | Turns (min to max) | Wall (min to max) | Cache-read tokens per flow | Output tokens per flow |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 14 | 14 (+1 flagged, flow cut short) | 14 | $0.037 ($0.031 to $0.047) | 43 (22 to 51) | 112 s (73 to 220) | 1.68M | 6.3k |
| claude-sonnet-5-5 | 12 | 15 | 15 | $0.489 ($0.442 to $0.523) | 43 (37 to 50) | 124 s (64 to 177) | 1.15M | 4.6k |
| claude-fable-5-1 | 14 | 15 | 14 | $2.52 ($2.37 to $2.72) | 41 (30 to 46) | 209 s (116 to 245) | 2.33M | 5.0k |

"Planted defect flagged" means every item the scripted user saw fail was reported as a fail. No
model missed a defect in a flow it finished, and all three reported the clean store clean. The
misses are of two kinds, below.

## Two flows the browser cut short (Haiku 1, Fable 1)

Both are the Chrome extension losing its tab, not a judgement.

- **Fable, `update-ignored`.** After the product page, Fable's reloads returned a browser error
  page for about 30 seconds. The store's request log stops at that product page and shows no
  error: the process was alive and idle, so the requests never left the browser. Fable reported
  items 3 to 10 as fail with a note that "the failures reflect an unavailable server rather than
  observed store defects".
- **Haiku, `add-ignores-quantity`.** Haiku saw item 3 fail (the badge said "Cart (1)" after adding
  2) and clicked the second "Add to cart"; the store log shows that click landed. Then "the Chrome
  extension disconnected" and the tab was unreachable. Haiku answered `not_run` for items 4 to 10
  and asked whether to restart from step 1. In a headless session nobody answers.

Each of the two coincides with one `computer` action (a zoom, a screenshot) recorded as a
permission denial, which fits an action sent to a tab the extension no longer had. None of the 55
cell-4 runs disconnected; 2 of 45 did here, on bigger pages. The grader now labels these
`incomplete` (the vector differs and the request log shows the flow did not finish) rather than
`wrong`; it is a mechanical label from the log, and `incomplete` still does not count as success.
The right response is a harness retry of that flow, not a bigger model: the model's honesty here
was fine on both tiers.

## Three Sonnet verdicts that over-reached

Sonnet drove all 15 flows to the end and flagged every planted defect, but in three flows it also
failed the item after the one the defect belongs to:

| Flow | Truth fails | Sonnet failed | Sonnet's reason for the extra fail |
|---|---|---|---|
| subtotal-skips-last | 6, 7 | 5, 6, 7 | "the Apexnest row's line total was $49.98 but the cart's Estimate ignored the Nordnest line" (item 5 checks only the rows, and the rows were right) |
| payment-method-ignored | 8 | 8, 9 | "the payment row read card refunded rather than paypal" (item 9 asks for status cancelled, the message, and payment status refunded; all three held) |
| order-tax-doubled | 8, 10 | 8, 9, 10 | "the payment amount was $57.27, not $54.12" (item 9 does not mention the amount) |

The pattern is the same each time: a defect already reported under its own item is carried into
the next item. Haiku and Fable, on the same three flows, matched the scripted user exactly. One can
defend Sonnet's readings as a customer (a refund of the wrong amount is a real complaint), but the
checklist names the fields each item checks, and the scripted user is the oracle. In cell 4 Fable
made the opposite slip (a lenient reading of one item). Rubric-boundary slips happen on every
tier; the planted defect itself was never missed by a model that finished the flow.

## Reading

1. **The family transfers to the user's own app.** On the real store Haiku judged every flow it
   finished exactly as the scripted user did, as it had on the toy app. Fable did the same. The
   checklist shape (numbered items, named fields, a server-rendered page read as text) is what
   makes a cheap tier safe, not the size of the app behind it.
2. **Cost per flow is 13x Haiku for Sonnet and 68x for Fable, and Fable takes twice as long.**
   Cache reads dominate again: about $0.017 of Haiku's $0.037, $0.23 of Sonnet's $0.49, $2.33 of
   Fable's $2.52. The pages are bigger than cell 4's, so Fable's context per turn grew to 2.3M
   cache-read tokens per flow.
3. **The new failure mode is the browser, not the model.** Two of 45 flows lost the extension tab.
   A bigger model does not fix that (one of the two was Fable). The request log gives a mechanical
   signal (`drove` is not `full`), so the rule is: retry an unfinished flow, do not step up.
4. **Routing decision:** unchanged, `haiku`, `low`, now with evidence from the user's own project.
   Add the retry rule to the family, and tell the agent to say which steps did not run when the
   browser disconnects, so the caller can retry instead of reading `fail` as a finding.

## Limits

- One trial per model (see the repeat trials below for what was re-run). 15 flows, one customer,
  one pair of products. Anthropic's bar for a production cutover is about 50 cases and 5 trials.
- The store was run without its DuckDB warehouse, so the home and product pages carry a
  "warehouse not built" note. Real app behaviour, and no model was distracted by it.
- The agents read the DOM as text. The visual parts of the store (the product grid, the chart on
  the analytics pages) were not judged from pixels.
- Two disconnects in 45 runs is too few to say what triggers them. Both happened on a `computer`
  action; the cell-4 flows used fewer of those.
