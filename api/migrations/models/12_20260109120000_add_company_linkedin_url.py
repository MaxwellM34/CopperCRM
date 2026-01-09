from tortoise import BaseDBAsyncClient #type: ignore


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "companies" ADD "linkedin_url" VARCHAR(255);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "companies" DROP COLUMN "linkedin_url";"""
