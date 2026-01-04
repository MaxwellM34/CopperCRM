from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "outbound_messages" ADD "step_id" INT REFERENCES "campaign_steps" ("id") ON DELETE SET NULL;
        ALTER TABLE "outbound_messages" ADD "llm_profile_version" VARCHAR(100);
        ALTER TABLE "outbound_messages" ADD "llm_profile_name" VARCHAR(255);
        ALTER TABLE "outbound_messages" ADD "llm_profile_rules" TEXT;
        ALTER TABLE "outbound_messages" ADD "llm_overlay_profile_version" VARCHAR(100);
        ALTER TABLE "outbound_messages" ADD "llm_overlay_profile_name" VARCHAR(255);
        ALTER TABLE "outbound_messages" ADD "llm_overlay_profile_rules" TEXT;

        ALTER TABLE "campaign_email_drafts" ADD "llm_profile_version" VARCHAR(100);
        ALTER TABLE "campaign_email_drafts" ADD "llm_profile_name" VARCHAR(255);
        ALTER TABLE "campaign_email_drafts" ADD "llm_profile_rules" TEXT;
        ALTER TABLE "campaign_email_drafts" ADD "llm_overlay_profile_version" VARCHAR(100);
        ALTER TABLE "campaign_email_drafts" ADD "llm_overlay_profile_name" VARCHAR(255);
        ALTER TABLE "campaign_email_drafts" ADD "llm_overlay_profile_rules" TEXT;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "campaign_email_drafts" DROP COLUMN "llm_overlay_profile_rules";
        ALTER TABLE "campaign_email_drafts" DROP COLUMN "llm_overlay_profile_name";
        ALTER TABLE "campaign_email_drafts" DROP COLUMN "llm_overlay_profile_version";
        ALTER TABLE "campaign_email_drafts" DROP COLUMN "llm_profile_rules";
        ALTER TABLE "campaign_email_drafts" DROP COLUMN "llm_profile_name";
        ALTER TABLE "campaign_email_drafts" DROP COLUMN "llm_profile_version";

        ALTER TABLE "outbound_messages" DROP COLUMN "llm_overlay_profile_rules";
        ALTER TABLE "outbound_messages" DROP COLUMN "llm_overlay_profile_name";
        ALTER TABLE "outbound_messages" DROP COLUMN "llm_overlay_profile_version";
        ALTER TABLE "outbound_messages" DROP COLUMN "llm_profile_rules";
        ALTER TABLE "outbound_messages" DROP COLUMN "llm_profile_name";
        ALTER TABLE "outbound_messages" DROP COLUMN "llm_profile_version";
        ALTER TABLE "outbound_messages" DROP COLUMN "step_id";
    """
