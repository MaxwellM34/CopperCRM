from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "campaigns" ADD "llm_overlay_profile_id" INT REFERENCES "llm_profiles" ("id") ON DELETE SET NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "campaigns" DROP COLUMN "llm_overlay_profile_id";
    """
