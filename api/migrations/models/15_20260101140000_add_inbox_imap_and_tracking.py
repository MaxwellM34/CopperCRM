from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "outbound_inboxes" ADD "imap_folder" VARCHAR(255);
        ALTER TABLE "outbound_inboxes" ADD "imap_sent_folder" VARCHAR(255);
        ALTER TABLE "outbound_inboxes" ADD "imap_last_uid" INT;
        ALTER TABLE "outbound_inboxes" ADD "imap_last_checked_at" TIMESTAMPTZ;

        ALTER TABLE "outbound_messages" ADD "recipient_email" VARCHAR(255);
        ALTER TABLE "outbound_messages" ADD "tracking_id" VARCHAR(255) UNIQUE;
        ALTER TABLE "outbound_messages" ADD "first_opened_at" TIMESTAMPTZ;
        ALTER TABLE "outbound_messages" ADD "last_opened_at" TIMESTAMPTZ;
        ALTER TABLE "outbound_messages" ADD "open_count" INT NOT NULL DEFAULT 0;

        ALTER TABLE "campaign_email_drafts" ADD "from_email" VARCHAR(255);
        ALTER TABLE "campaign_email_drafts" ADD "to_email" VARCHAR(255);
        ALTER TABLE "campaign_email_drafts" ADD "step_id" INT REFERENCES "campaign_steps" ("id") ON DELETE SET NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "campaign_email_drafts" DROP COLUMN "step_id";
        ALTER TABLE "campaign_email_drafts" DROP COLUMN "to_email";
        ALTER TABLE "campaign_email_drafts" DROP COLUMN "from_email";

        ALTER TABLE "outbound_messages" DROP COLUMN "open_count";
        ALTER TABLE "outbound_messages" DROP COLUMN "last_opened_at";
        ALTER TABLE "outbound_messages" DROP COLUMN "first_opened_at";
        ALTER TABLE "outbound_messages" DROP COLUMN "tracking_id";
        ALTER TABLE "outbound_messages" DROP COLUMN "recipient_email";

        ALTER TABLE "outbound_inboxes" DROP COLUMN "imap_last_checked_at";
        ALTER TABLE "outbound_inboxes" DROP COLUMN "imap_last_uid";
        ALTER TABLE "outbound_inboxes" DROP COLUMN "imap_sent_folder";
        ALTER TABLE "outbound_inboxes" DROP COLUMN "imap_folder";
    """
