from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "leads" ADD COLUMN IF NOT EXISTS "gender" VARCHAR(20) NOT NULL DEFAULT 'unknown_gender';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "leads" DROP COLUMN IF EXISTS "gender";
    """
