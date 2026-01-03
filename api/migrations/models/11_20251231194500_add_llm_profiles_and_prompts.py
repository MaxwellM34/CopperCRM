from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "llm_profiles" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "description" TEXT,
    "rules" TEXT NOT NULL,
    "is_default" BOOL NOT NULL  DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
        ALTER TABLE "campaigns" ADD "llm_profile_id" INT REFERENCES "llm_profiles" ("id") ON DELETE SET NULL;
        ALTER TABLE "campaign_steps" ADD "prompt_template" TEXT;
        CREATE INDEX IF NOT EXISTS "idx_llm_profiles_is_default" ON "llm_profiles" ("is_default");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "campaign_steps" DROP COLUMN "prompt_template";
        ALTER TABLE "campaigns" DROP COLUMN "llm_profile_id";
        DROP TABLE IF EXISTS "llm_profiles";
    """
