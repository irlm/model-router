# Cell 5: the author's own web store through the Chrome extension (2026-10-30)

The browser-flow family of cell 4 repeated on a real application: the Go store of the user's
author's own Go store (Postgres, server-rendered templates, one
small `app.js`), at commit `24211d9`. 15 flows (14 planted defects plus a clean store), a numbered
10-item checklist, three models at effort low: two trials for Haiku and Sonnet, one for Fable plus
a rerun of its one lost flow. The
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

## Trial 2 (run about two hours later, same browser)

| Model | Correct / 15 | Planted defect flagged | Flow finished / 15 | Cost per flow (min to max) | Turns (min to max) | Wall (min to max) | Cache-read tokens per flow | Output tokens per flow |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 14 | 14 of 14 finished | 14 | $0.038 ($0.032 to $0.043) | 41 (23 to 48) | 181 s (103 to 340) | 1.68M | 6.4k |
| claude-sonnet-5-5 | 13 | 14 of 14 finished | 14 | $0.464 ($0.320 to $0.497) | 39 (14 to 43) | 139 s (29 to 212) | 1.04M | 4.1k |
| claude-fable-5-1 (rerun of the one lost flow only) | 1 of 1 | 1 of 1 | 1 | $3.03 | 56 | 408 s | 3.50M | 7.5k |

Over both trials: Haiku 28/30, Sonnet 25/30, Fable 15/16. Among flows the browser let finish:
Haiku 28/28, Fable 15/15, Sonnet 25/29.

**Reruns (trial 3).** After the cause of the disconnects was known (below), the three flows cut
short in trials 1 and 2 that had not yet been rerun were run once more: Haiku on
`add-ignores-quantity` and `cancel-no-status`, Sonnet on `cart-shows-cost-price`. All three drove
the full flow and matched the scripted user ($0.039, $0.036, $0.542; 120 s, 204 s, 168 s). With
Fable's rerun from trial 2, every cut flow now has a finished, correct run. Totals over every run:
Haiku 30 correct of 32 (30/30 finished), Sonnet 26 of 31 (26/30 finished), Fable 15 of 16 (15/15
finished). Mean cost per flow over everything run: Haiku
$0.038, Sonnet $0.476, Fable $2.55; mean wall 147 s / 131 s / 222 s. Trial 2 was slower
for the same turn counts (Haiku 181 s against 112 s), so the browser or the machine was slower, not
the model.

## Four flows the browser cut short (Haiku 2, Sonnet 1, Fable 1)

All four are the Chrome extension losing its tab, not a judgement. Trial 1:

- **Fable, `update-ignored`.** After the product page, Fable's reloads returned a browser error
  page for about 30 seconds. The store's request log stops at that product page and shows no
  error: the process was alive and idle, so the requests never left the browser. Fable reported
  items 3 to 10 as fail with a note that "the failures reflect an unavailable server rather than
  observed store defects".
- **Haiku, `add-ignores-quantity`.** Haiku saw item 3 fail (the badge said "Cart (1)" after adding
  2) and clicked the second "Add to cart"; the store log shows that click landed. Then "the Chrome
  extension disconnected" and the tab was unreachable. Haiku answered `not_run` for items 4 to 10
  and asked whether to restart from step 1. In a headless session nobody answers.

Trial 2:

- **Sonnet, `cart-shows-cost-price`.** The store answered the first home-page request and then
  nothing: the browser showed an error page on both of Sonnet's attempts. Sonnet stopped after 14
  turns and reported every item fail, with the note "not because of anything seen in the store".
- **Haiku, `cancel-no-status`.** Haiku drove the flow to "Place order"; the store log shows the
  checkout and the order page served. Then "the browser tab group was reset before the result page
  could be read" and the tab was closed. Haiku reported 8 as fail and 9 and 10 as not reached.

Three of the four coincide with a browser action recorded as a permission denial (a zoom, a
screenshot, a click), which fits an action sent to a tab the extension no longer had. None of the
55 cell-4 runs disconnected; 4 of 76 did here, on all three tiers. Cause, found after the runs: the
user closed the browser by mistake while the trials ran. The runs share the user's real Chrome, so
a closed window takes the extension's tab with it. The grader labels these
`incomplete` (the vector differs and the request log shows the flow did not finish) rather than
`wrong`; it is a mechanical label from the log, and `incomplete` still does not count as success.
The right response is a harness retry of that flow, not a bigger model: the models were honest
about it on every tier, and all four flows were rerun afterwards and every rerun finished and was correct.

## Four Sonnet verdicts that over-reached (three in trial 1, one in trial 2)

Sonnet flagged every planted defect in every flow it finished, but in four flows it also failed
the item after the one the defect belongs to:

| Flow | Truth fails | Sonnet failed | Sonnet's reason for the extra fail |
|---|---|---|---|
| subtotal-skips-last | 6, 7 | 5, 6, 7 | "the Apexnest row's line total was $49.98 but the cart's Estimate ignored the Nordnest line" (item 5 checks only the rows, and the rows were right) |
| payment-method-ignored | 8 | 8, 9 | "the payment row read card refunded rather than paypal" (item 9 asks for status cancelled, the message, and payment status refunded; all three held) |
| order-tax-doubled | 8, 10 | 8, 9, 10 | "the payment amount was $57.27, not $54.12" (item 9 does not mention the amount) |
| update-ignored (trial 2) | 7, 8, 10 | 7, 8, 9, 10 | "the order shows the card payment refunded and not a PayPal one" (Sonnet also said it could not change the payment method; the planted defect does not touch payment, so the PayPal choice was most likely lost in its own form handling; item 9 still checks only status, message and "refunded") |

The pattern is the same each time: a defect already reported under its own item is carried into
the next item. Haiku and Fable, on the same flows, matched the scripted user exactly. One can
defend Sonnet's readings as a customer (a refund of the wrong amount is a real complaint), but the
checklist names the fields each item checks, and the scripted user is the oracle. In cell 4 Fable
made the opposite slip (a lenient reading of one item). Rubric-boundary slips happen on every
tier; the planted defect itself was never missed by a model that finished the flow.

## Reading

1. **The family transfers to the user's own app.** On the real store Haiku judged every flow it
   finished exactly as the scripted user did, 28 of 28 over two trials, as it had on the toy app.
   Fable did the same, 15 of 15. Sonnet was the one tier with judgement misses, 4 of 29. The
   checklist shape (numbered items, named fields, a server-rendered page read as text) is what
   makes a cheap tier safe, not the size of the app behind it.
2. **Cost per flow is 13x Haiku for Sonnet and 68x for Fable, and Fable takes twice as long.**
   Cache reads dominate again: about $0.017 of Haiku's $0.037, $0.23 of Sonnet's $0.49, $2.33 of
   Fable's $2.52. The pages are bigger than cell 4's, so Fable's context per turn grew to 2.3M
   cache-read tokens per flow.
3. **The new failure mode is the browser, not the model.** Four of 76 flows lost the extension tab,
   on all three tiers. A bigger model does not fix that. The request log gives a mechanical
   signal (`drove` is not `full`), so the rule is: retry an unfinished flow, do not step up.
4. **Routing decision:** unchanged, `haiku`, `low`, now with evidence from the user's own project.
   Add the retry rule to the family, and tell the agent to say which steps did not run when the
   browser disconnects, so the caller can retry instead of reading `fail` as a finding.

## Limits

- Two trials for Haiku and Sonnet, one for Fable plus a rerun of one flow. 15 flows, one customer,
  one pair of products. Anthropic's bar for a production cutover is about 50 cases and 5 trials.
- The store was run without its DuckDB warehouse, so the home and product pages carry a
  "warehouse not built" note. Real app behaviour, and no model was distracted by it.
- The agents read the DOM as text. The visual parts of the store (the product grid, the chart on
  the analytics pages) were not judged from pixels.
- The four disconnects were the shared Chrome being closed by hand, so they say nothing about the
  extension's own reliability. The retry rule still stands: in real use the browser is shared with a
  person too.
