from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "first_email_approvals" ADD COLUMN IF NOT EXISTS "human_reviewed" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "first_email_approvals" ALTER COLUMN "human_approval" SET DEFAULT False;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "first_email_approvals" DROP COLUMN IF EXISTS "human_reviewed";
        ALTER TABLE "first_email_approvals" ALTER COLUMN "human_approval" DROP DEFAULT;
    """
