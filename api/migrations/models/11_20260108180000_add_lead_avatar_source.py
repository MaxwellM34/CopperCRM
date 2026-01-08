from tortoise import BaseDBAsyncClient #type: ignore


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "leads" ADD "created_source" VARCHAR(50);
        ALTER TABLE "leads" ADD "updated_source" VARCHAR(50);
        ALTER TABLE "leads" ADD "avatar_url" VARCHAR(1024);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "leads" DROP COLUMN "avatar_url";
        ALTER TABLE "leads" DROP COLUMN "updated_source";
        ALTER TABLE "leads" DROP COLUMN "created_source";"""
