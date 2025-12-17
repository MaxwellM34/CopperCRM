from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "first_email_approvals" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "overall_approval" BOOL NOT NULL  DEFAULT False,
    "algorithm_approval" BOOL NOT NULL  DEFAULT False,
    "human_approval" BOOL,
    "structure_and_clarity" INT NOT NULL,
    "deliverability" INT NOT NULL,
    "value_proposition" INT NOT NULL,
    "customer_reaction" INT NOT NULL,
    "first_email_id" INT UNIQUE REFERENCES "first_email" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "first_email_approvals";"""
