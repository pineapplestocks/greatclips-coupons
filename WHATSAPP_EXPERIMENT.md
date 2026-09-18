# WhatsApp popup experiment

`wa-popup-v1` compares A (Kumar personal introduction), B (short coupon-first), and C (coupon plus ongoing deals). Copy is frozen in `cloudflare-worker/whatsapp-experiment.js`. Preview all three at `/whatsapp-preview.html?wa_preview=A` (or B/C); previews never create coupon requests or tracked exposures.

## Measurement

Server hashing assigns approximately one third of random browser IDs to each variant. Local storage keeps the browser ID for 90 days. Only opening the popup counts as an exposure. Count unique browsers, not people across devices. Track views, clicks, no-click-yet viewers, dismissals, sent requests, verified membership and coupon delivery. The primary outcome is verified membership per exposed browser within seven days; this includes existing members. Observed new joins require a nonmember check followed by a confirmed member check. Joining before the first check can look like existing membership, so observed joins are a lower bound.

Enrollment runs 28 days from migration 005, then seven days are allowed for outcomes on attributed requests. Assignment and new request attribution stop at enrollment close; the normal control popup continues. No automatic winning-design rollout occurs. The report waits until day 35, requires 500 mature viewers and at least 20 member/nonmember outcomes per variant, checks gross assignment imbalance, and uses conservative corrected pairwise normal-approximation tests (z >= 2.40) before naming a winner. Otherwise it reports insufficient or inconclusive evidence. Cards show descriptive 95% Wilson intervals. Do not repeatedly stop early or change copy within this experiment; use a new experiment ID for the next test.

Previews, preexisting saved requests, tracking opt-outs (DNT/GPC), storage failures, analytics failures and assignments above the IP abuse cap are excluded. These visitors can still request coupons. Results describe eligible browsers, not all site visitors. Individual experiment records expire after 90 days; the scheduled worker archives an aggregate final report before cleanup.

## Operations

Apply migrations 002 through 005 in order, deploy the worker with `--config wrangler.toml --keep-vars`, deploy docs, and restart the existing supervised bot to enable the initial membership check before invitations. Run `node --test tests/whatsapp.test.mjs tests/whatsapp-experiment.test.mjs` and the bot coupon-gate tests.

Open `/whatsapp-experiment.html` and enter the existing ADMIN_TOKEN. The password stays in page memory, never URLs or browser storage. The local ignored `.cache/whatsapp-experiment-access.txt` contains owner access details. This is a read-only analytics dashboard, not an approval queue. It supports live/mature views and CSV export.

To pause enrollment, set WHATSAPP_EXPERIMENT_ENABLED to false and redeploy the worker. Coupon delivery continues with the control popup. Keep the supervised WhatsApp bot online for membership and delivery measurements. Aggregate reporting remains available.

Method references: [NIST Bonferroni comparisons](https://itl.nist.gov/div898/handbook/prc/section4/prc473.htm), [NIST binomial proportion intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).
