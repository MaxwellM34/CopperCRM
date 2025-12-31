-- 01_inspect_leads.sql
-- Read-only: basic sanity checks on mautic.leads

-- Total number of leads
SELECT COUNT(*) AS total_leads
FROM mautic.leads;

-- How many leads have no owner
SELECT COUNT(*) AS leads_without_owner
FROM mautic.leads
WHERE owner_id IS NULL;

-- How many leads have no email AND no name
SELECT COUNT(*) AS no_email_no_name
FROM mautic.leads
WHERE (email IS NULL OR email = '')
  AND (firstname IS NULL OR firstname = '')
  AND (lastname IS NULL OR lastname = '');

-- Sample of "no email + no name" leads (to eyeball before deleting)
SELECT id,
       owner_id,
       email,
       firstname,
       lastname
FROM mautic.leads
WHERE (email IS NULL OR email = '')
  AND (firstname IS NULL OR firstname = '')
  AND (lastname IS NULL OR lastname = '')
ORDER BY id
LIMIT 50;

-- Recent leads (last 7 days) – just to confirm real stuff still exists
SELECT id,
       owner_id,
       email,
       firstname,
       lastname,
       date_added
FROM mautic.leads
WHERE date_added > NOW() - INTERVAL 7 DAY
ORDER BY date_added DESC
LIMIT 50;
