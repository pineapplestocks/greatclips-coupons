-- Brevo export queries for the greatclips-subscribers D1 database.
--
-- Paste ONE statement at a time into the D1 Studio query editor
-- (Cloudflare dashboard > D1 > greatclips-subscribers > Studio), then use the
-- export/download control on the results grid to get a CSV.
--
-- These are SQL, not shell commands. The `python scripts/export_subscribers.py`
-- variants do the same thing from a terminal, and are better if Studio truncates
-- large result sets.
--
-- Column aliases are uppercase on purpose: Brevo maps a column literally named
-- EMAIL to the contact address, and imports the rest as contact attributes.


-- ============================================================
-- STEP 1 -- Sanity check. Run this first.
-- ============================================================
-- The worker counts COUNT(*) and COUNT(DISTINCT lower(email)) separately in its
-- admin summary, so duplicates exist: your "9,000" is rows, and the real
-- mailable list is probably smaller. This tells you the true number and how far
-- back the list goes.

SELECT
  COUNT(*)                                AS total_rows,
  COUNT(DISTINCT lower(trim(email)))      AS unique_emails,
  MIN(subscribed_at)                      AS oldest_signup,
  MAX(subscribed_at)                      AS newest_signup
FROM subscribers;


-- ============================================================
-- STEP 2 -- Batch 1: the newest 1,000 contacts.
-- ============================================================
-- Newest first, because recent subscribers are the most engaged and the least
-- likely to have gone stale. This list has never received a bulk send, so mail
-- this batch, check bounce and complaint rates, and only then continue.
-- Hard bounces over ~5% can get the Brevo account suspended, which would take
-- down coupon delivery site-wide.

SELECT
  lower(trim(email))          AS EMAIL,
  COALESCE(zip_code, '')      AS ZIP_CODE,
  COALESCE(city, '')          AS CITY,
  COALESCE(state, '')         AS STATE,
  subscribed_at               AS SUBSCRIBED_AT
FROM (
  SELECT email, zip_code, city, state, subscribed_at,
         ROW_NUMBER() OVER (
           PARTITION BY lower(trim(email))
           ORDER BY subscribed_at DESC
         ) AS rn
  FROM subscribers
  WHERE email LIKE '%_@_%.__%'   -- drop anything that is not address-shaped
)
WHERE rn = 1                     -- keep the most recent row per address
ORDER BY subscribed_at DESC
LIMIT 1000 OFFSET 0;


-- ============================================================
-- STEP 3 -- Later batches: same query, change the last line only.
-- ============================================================
--   batch 2 (next 2,000):  LIMIT 2000 OFFSET 1000;
--   the rest:              LIMIT -1   OFFSET 3000;
--
-- LIMIT -1 means "no limit" in SQLite. Keep ORDER BY subscribed_at DESC
-- identical across batches or the offsets will overlap and you will mail
-- some people twice.
