from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "users" RENAME COLUMN "can_review" TO "is_admin";
        ALTER TABLE "users" ADD "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" RENAME COLUMN "is_admin" TO "can_review";
        ALTER TABLE "users" DROP COLUMN "updated_at";
        ALTER TABLE "users" DROP COLUMN "created_at";"""
