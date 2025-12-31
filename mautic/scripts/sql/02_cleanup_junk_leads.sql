-- 02_cleanup_junk_leads.sql

-- === 1. PREVIEW (SAFE) ===
SELECT id,
       owner_id,
       email,
       firstname,
       lastname
FROM mautic.leads
WHERE owner_id IS NULL
  AND (email IS NULL OR email = '')
  AND (firstname IS NULL OR firstname = '')
  AND (lastname IS NULL OR lastname = '')
ORDER BY id


LIMIT 200;

-- === 2. DELETE (UNCOMMENT TO RUN) ===
DELETE
FROM mautic.leads
WHERE owner_id IS NULL
  AND (email IS NULL OR email = '')
  AND (firstname IS NULL OR firstname = '')
  AND (lastname IS NULL OR lastname = '');
