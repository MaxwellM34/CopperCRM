from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "llm_profiles" ADD "category" VARCHAR(50) NOT NULL  DEFAULT 'general';
        ALTER TABLE "first_email"
            ADD "llm_profile_version" VARCHAR(100),
            ADD "llm_profile_name" VARCHAR(255),
            ADD "llm_profile_rules" TEXT,
            ADD "llm_overlay_profile_version" VARCHAR(100),
            ADD "llm_overlay_profile_name" VARCHAR(255),
            ADD "llm_overlay_profile_rules" TEXT;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "first_email" DROP COLUMN "llm_overlay_profile_rules";
        ALTER TABLE "first_email" DROP COLUMN "llm_overlay_profile_name";
        ALTER TABLE "first_email" DROP COLUMN "llm_overlay_profile_version";
        ALTER TABLE "first_email" DROP COLUMN "llm_profile_rules";
        ALTER TABLE "first_email" DROP COLUMN "llm_profile_name";
        ALTER TABLE "first_email" DROP COLUMN "llm_profile_version";
        ALTER TABLE "llm_profiles" DROP COLUMN "category";
    """
