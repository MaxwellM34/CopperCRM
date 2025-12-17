from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "first_email_approvals" ALTER COLUMN "structure_and_clarity" DROP NOT NULL;
        ALTER TABLE "first_email_approvals" ALTER COLUMN "deliverability" DROP NOT NULL;
        ALTER TABLE "first_email_approvals" ALTER COLUMN "value_proposition" DROP NOT NULL;
        ALTER TABLE "first_email_approvals" ALTER COLUMN "customer_reaction" DROP NOT NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "first_email_approvals" ALTER COLUMN "structure_and_clarity" SET NOT NULL;
        ALTER TABLE "first_email_approvals" ALTER COLUMN "deliverability" SET NOT NULL;
        ALTER TABLE "first_email_approvals" ALTER COLUMN "value_proposition" SET NOT NULL;
        ALTER TABLE "first_email_approvals" ALTER COLUMN "customer_reaction" SET NOT NULL;
    """
