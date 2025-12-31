-- 03_cleanup_orphan_references.sql
-- Clean orphan records that reference deleted leads

-- Segments membership
DELETE FROM mautic.lead_lists_leads
WHERE lead_id NOT IN (SELECT id FROM mautic.leads);

-- Campaign membership
DELETE FROM mautic.campaign_leads
WHERE lead_id NOT IN (SELECT id FROM mautic.leads);

-- Tags
DELETE FROM mautic.lead_tags_xref
WHERE lead_id NOT IN (SELECT id FROM mautic.leads);


-- Email stats
DELETE FROM mautic.email_stats
WHERE lead_id NOT IN (SELECT id FROM mautic.leads);
