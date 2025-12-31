#!/bin/bash

CRON_FILE="/srv/mautic/cron/mautic-cron.txt"

echo "Installing Mautic cron jobs from $CRON_FILE..."

# Wipe current crontab for this user
crontab -r 2>/dev/null || true

# Get current crontab, remove existing mautic jobs, append fresh ones
crontab -l 2>/dev/null | \
grep -v "mautic-app php /var/www/html/bin/console" | \
grep -v "/srv/backup_mautic.sh" \
> /tmp/cron_clean || true

cat "$CRON_FILE" >> /tmp/cron_clean

crontab /tmp/cron_clean
rm /tmp/cron_clean

echo "Cron installation complete!"
