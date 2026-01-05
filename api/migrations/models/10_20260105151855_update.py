from tortoise import BaseDBAsyncClient #type: ignore


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "stages" ADD "stage" VARCHAR(8) NOT NULL  DEFAULT 'freezing';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "stages" DROP COLUMN "stage";"""
