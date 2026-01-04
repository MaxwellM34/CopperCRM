from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "leads" ADD "opted_out" BOOL NOT NULL  DEFAULT False;
        ALTER TABLE "leads" ADD "opted_out_at" TIMESTAMPTZ;
        ALTER TABLE "leads" ADD "points" INT NOT NULL  DEFAULT 0;
        ALTER TABLE "leads" ADD "last_activity_at" TIMESTAMPTZ;
        ALTER TABLE "leads" ADD "last_activity_type" VARCHAR(50);

        CREATE TABLE IF NOT EXISTS "outbound_inboxes" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "email_address" VARCHAR(255) NOT NULL UNIQUE,
    "display_name" VARCHAR(255),
    "domain" VARCHAR(255) NOT NULL,
    "subdomain" VARCHAR(255),
    "ses_identity" VARCHAR(255),
    "ses_configuration_set" VARCHAR(255),
    "daily_cap" INT NOT NULL  DEFAULT 200,
    "daily_sent" INT NOT NULL  DEFAULT 0,
    "last_reset_at" TIMESTAMPTZ,
    "active" BOOL NOT NULL  DEFAULT True,
    "imap_host" VARCHAR(255),
    "imap_port" INT,
    "imap_use_ssl" BOOL NOT NULL  DEFAULT True,
    "imap_username" VARCHAR(255),
    "imap_password" VARCHAR(255),
    "reply_to" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);

        CREATE TABLE IF NOT EXISTS "campaign_edges" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "condition_type" VARCHAR(50) NOT NULL  DEFAULT 'always',
    "condition_value" TEXT,
    "label" VARCHAR(255),
    "order" INT NOT NULL  DEFAULT 1,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "campaign_id" INT NOT NULL REFERENCES "campaigns" ("id") ON DELETE CASCADE,
    "from_step_id" INT NOT NULL REFERENCES "campaign_steps" ("id") ON DELETE CASCADE,
    "to_step_id" INT NOT NULL REFERENCES "campaign_steps" ("id") ON DELETE CASCADE
);

        CREATE TABLE IF NOT EXISTS "lead_campaign_states" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "status" VARCHAR(50) NOT NULL  DEFAULT 'pending',
    "next_step_at" TIMESTAMPTZ,
    "last_sent_at" TIMESTAMPTZ,
    "last_activity_at" TIMESTAMPTZ,
    "thread_id" VARCHAR(255),
    "last_message_id" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "lead_id" INT NOT NULL REFERENCES "leads" ("id") ON DELETE CASCADE,
    "campaign_id" INT NOT NULL REFERENCES "campaigns" ("id") ON DELETE CASCADE,
    "current_step_id" INT REFERENCES "campaign_steps" ("id") ON DELETE SET NULL,
    "assigned_inbox_id" INT REFERENCES "outbound_inboxes" ("id") ON DELETE SET NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS "uid_lead_campaign" ON "lead_campaign_states" ("lead_id", "campaign_id");

        CREATE TABLE IF NOT EXISTS "lead_activities" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "activity_type" VARCHAR(50) NOT NULL,
    "occurred_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "metadata" JSONB NOT NULL  DEFAULT '{}'::jsonb,
    "lead_id" INT NOT NULL REFERENCES "leads" ("id") ON DELETE CASCADE,
    "campaign_id" INT REFERENCES "campaigns" ("id") ON DELETE SET NULL,
    "inbox_id" INT REFERENCES "outbound_inboxes" ("id") ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS "idx_lead_activities_lead" ON "lead_activities" ("lead_id");

        CREATE TABLE IF NOT EXISTS "outbound_messages" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "direction" VARCHAR(20) NOT NULL  DEFAULT 'outbound',
    "message_id" VARCHAR(255) NOT NULL UNIQUE,
    "thread_id" VARCHAR(255),
    "subject" VARCHAR(255),
    "in_reply_to" VARCHAR(255),
    "references" TEXT,
    "sent_at" TIMESTAMPTZ,
    "status" VARCHAR(50) NOT NULL  DEFAULT 'sent',
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "lead_id" INT NOT NULL REFERENCES "leads" ("id") ON DELETE CASCADE,
    "campaign_id" INT REFERENCES "campaigns" ("id") ON DELETE SET NULL,
    "inbox_id" INT REFERENCES "outbound_inboxes" ("id") ON DELETE SET NULL
);

        CREATE TABLE IF NOT EXISTS "campaign_email_drafts" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "subject" VARCHAR(255),
    "body_text" TEXT NOT NULL,
    "body_html" TEXT,
    "status" VARCHAR(50) NOT NULL  DEFAULT 'pending',
    "approved_at" TIMESTAMPTZ,
    "sent_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "campaign_id" INT NOT NULL REFERENCES "campaigns" ("id") ON DELETE CASCADE,
    "lead_id" INT NOT NULL REFERENCES "leads" ("id") ON DELETE CASCADE,
    "inbox_id" INT REFERENCES "outbound_inboxes" ("id") ON DELETE SET NULL,
    "approved_by_id" INT REFERENCES "users" ("id") ON DELETE SET NULL
);
"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "campaign_email_drafts";
        DROP TABLE IF EXISTS "outbound_messages";
        DROP TABLE IF EXISTS "lead_activities";
        DROP TABLE IF EXISTS "lead_campaign_states";
        DROP TABLE IF EXISTS "campaign_edges";
        DROP TABLE IF EXISTS "outbound_inboxes";

        ALTER TABLE "leads" DROP COLUMN "last_activity_type";
        ALTER TABLE "leads" DROP COLUMN "last_activity_at";
        ALTER TABLE "leads" DROP COLUMN "points";
        ALTER TABLE "leads" DROP COLUMN "opted_out_at";
        ALTER TABLE "leads" DROP COLUMN "opted_out";
    """
