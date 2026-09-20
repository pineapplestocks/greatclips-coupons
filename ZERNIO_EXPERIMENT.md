# Official WhatsApp popup experiment

A: savings, B: short coupon-first, C: personal invitation from Kumar. Real visitors receive stable anonymous browser assignments approximately 1:1:1. Same selected offer, steps and CTA. Preview and tracking-protection browsers are excluded. Failures fall back to control without blocking coupons.

Primary outcome: provider-accepted coupon sends per popup viewer within seven days. Secondary stages: click, request creation, actual incoming WhatsApp message, self-confirmation. Self-confirmation is not verified membership; accepted send is not delivered/read. Close and pagehide exit counts overlap and may miss terminations; no-click count measures non-conversion more reliably. Unique-browser counts differ from GA4 event counts.

28-day enrollment plus seven-day follow-up. Existing requests can finish after enrollment; new requests after enrollment are unattributed. Fixed-horizon assessment checks sample size, traffic balance and corrected comparisons. No automatic winner promotion. Control returns after enrollment. Aggregate report archived before individual data expires after 90 days.

Dashboard: https://greatclipsdeal.com/zernio-experiment.html. ADMIN_TOKEN required, held only in tab memory. Ignored local access file: .cache/zernio-experiment-access.txt. Preview /zernio-preview.html?zernio_preview=A (also B/C) never creates coupon requests or analytics events.

Existing GA4 tag: G-90ZQ7M4EFR. Events: coupon_popup_view, coupon_popup_click, coupon_popup_dismiss, coupon_popup_exit. Parameters: experiment_id, variant, page_type. No phone, request reference or experiment browser ID is sent as a custom parameter. Register event-scoped custom dimensions for variant and experiment_id in GA4 Admin > Custom definitions, then build a view-to-click funnel exploration with Variant breakdown. These property-side settings have not been created by this deployment. No second tag or Measurement Protocol secret is needed. The private dashboard additionally joins WhatsApp outcomes; GA4 receives website events only.
