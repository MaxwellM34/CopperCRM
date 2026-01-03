from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "campaigns" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "category" VARCHAR(50) NOT NULL  DEFAULT 'cold_outbound',
    "status" VARCHAR(50) NOT NULL  DEFAULT 'draft',
    "preset_key" VARCHAR(100),
    "audience_size" INT,
    "entry_point" VARCHAR(255),
    "ai_brief" TEXT,
    "launch_notes" TEXT,
    "launched_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "created_by_id" INT REFERENCES "users" ("id") ON DELETE SET NULL,
    "updated_by_id" INT REFERENCES "users" ("id") ON DELETE SET NULL,
    "launched_by_id" INT REFERENCES "users" ("id") ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS "idx_campaigns_category_status" ON "campaigns" ("category", "status");
        CREATE TABLE IF NOT EXISTS "campaign_steps" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "title" VARCHAR(255) NOT NULL,
    "step_type" VARCHAR(50) NOT NULL,
    "sequence" INT NOT NULL  DEFAULT 1,
    "lane" VARCHAR(50),
    "config" JSONB NOT NULL  DEFAULT '{}'::jsonb,
    "position_x" INT,
    "position_y" INT,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "campaign_id" INT NOT NULL REFERENCES "campaigns" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_campaign_steps_campaign_seq" ON "campaign_steps" ("campaign_id", "sequence");
CREATE UNIQUE INDEX IF NOT EXISTS "uid_campaign_steps_campaign_seq_title" ON "campaign_steps" ("campaign_id", "sequence", "title");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "campaign_steps";
        DROP TABLE IF EXISTS "campaigns";"""
