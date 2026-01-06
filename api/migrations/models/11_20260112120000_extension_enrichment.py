from tortoise import BaseDBAsyncClient #type: ignore


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD "can_use_extension" BOOL NOT NULL  DEFAULT False;
        ALTER TABLE "leads" ADD "linkedin_url" VARCHAR(255) UNIQUE;
        ALTER TABLE "leads" ADD "linkedin_headline" VARCHAR(255);
        ALTER TABLE "leads" ADD "linkedin_company_name" VARCHAR(255);
        ALTER TABLE "leads" ADD "avatar_bytes" BYTEA;
        ALTER TABLE "leads" ADD "avatar_content_type" VARCHAR(100);
        ALTER TABLE "leads" ADD "linkedin_updated_at" TIMESTAMPTZ;
        ALTER TABLE "leads" ADD "last_collected_at" TIMESTAMPTZ;
        ALTER TABLE "leads" ADD "last_collected_by_id" INT REFERENCES "users" ("id") ON DELETE SET NULL;
        CREATE TABLE IF NOT EXISTS "threads" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "source" VARCHAR(20) NOT NULL,
            "collected_at" TIMESTAMPTZ,
            "external_thread_id" VARCHAR(255),
            "thread_fingerprint" VARCHAR(64),
            "lead_id" INT NOT NULL REFERENCES "leads" ("id") ON DELETE CASCADE,
            "collected_by_id" INT REFERENCES "users" ("id") ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS "idx_threads_lead_source_external" ON "threads" ("lead_id", "source", "external_thread_id");
        CREATE INDEX IF NOT EXISTS "idx_threads_fingerprint" ON "threads" ("thread_fingerprint");
        CREATE TABLE IF NOT EXISTS "thread_messages" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "source" VARCHAR(20) NOT NULL,
            "direction" VARCHAR(20) NOT NULL,
            "message_at" TIMESTAMPTZ,
            "encrypted_content" BYTEA NOT NULL,
            "content_hash" VARCHAR(64),
            "external_message_id" VARCHAR(255),
            "thread_id" INT NOT NULL REFERENCES "threads" ("id") ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS "idx_thread_messages_thread_external" ON "thread_messages" ("thread_id", "external_message_id");
        CREATE INDEX IF NOT EXISTS "idx_thread_messages_content_hash" ON "thread_messages" ("content_hash");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "thread_messages";
        DROP TABLE IF EXISTS "threads";
        ALTER TABLE "leads" DROP COLUMN "last_collected_by_id";
        ALTER TABLE "leads" DROP COLUMN "last_collected_at";
        ALTER TABLE "leads" DROP COLUMN "linkedin_updated_at";
        ALTER TABLE "leads" DROP COLUMN "avatar_content_type";
        ALTER TABLE "leads" DROP COLUMN "avatar_bytes";
        ALTER TABLE "leads" DROP COLUMN "linkedin_company_name";
        ALTER TABLE "leads" DROP COLUMN "linkedin_headline";
        ALTER TABLE "leads" DROP COLUMN "linkedin_url";
        ALTER TABLE "users" DROP COLUMN "can_use_extension";"""
