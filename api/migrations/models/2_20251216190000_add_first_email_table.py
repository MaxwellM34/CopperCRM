from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "first_email" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "first_email" TEXT NOT NULL,
    "approval" BOOL NOT NULL  DEFAULT False,
    "model" VARCHAR(100),
    "prompt_tokens" INT,
    "completion_tokens" INT,
    "total_tokens" INT,
    "cost_usd" DECIMAL(10,6),
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "human_edited" BOOL NOT NULL  DEFAULT False,
    "pre_human_edit" TEXT,
    "post_human_edit" TEXT,
    "pre_editor" TEXT,
    "post_editor" TEXT,
    "edited_by" VARCHAR(255),
    "lead_id" INT NOT NULL REFERENCES "leads" ("id") ON DELETE CASCADE,
    "created_by_id" INT REFERENCES "users" ("id") ON DELETE SET NULL,
    "updated_by_id" INT REFERENCES "users" ("id") ON DELETE SET NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS "uid_first_email_lead_id" ON "first_email" ("lead_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "first_email";"""
