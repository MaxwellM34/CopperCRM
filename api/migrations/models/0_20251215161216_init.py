from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "users" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "firstname" VARCHAR(100) NOT NULL,
    "lastname" VARCHAR(100),
    "can_review" BOOL NOT NULL  DEFAULT False,
    "disabled" BOOL NOT NULL  DEFAULT False
);
CREATE TABLE IF NOT EXISTS "compaies" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "company_name" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "employees_amount" VARCHAR(100),
    "company_address" VARCHAR(255),
    "company_city" VARCHAR(255),
    "company_phone" VARCHAR(255),
    "company_email" VARCHAR(255),
    "technologies" VARCHAR(255),
    "latest_funding" VARCHAR(255),
    "lastest_funding_date" DATE,
    "facebook" VARCHAR(255),
    "twitter" VARCHAR(255),
    "youtube" VARCHAR(255),
    "instagram" VARCHAR(255),
    "annual_revenue" VARCHAR(255),
    "created_by_id" INT REFERENCES "users" ("id") ON DELETE SET NULL,
    "updated_by_id" INT REFERENCES "users" ("id") ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS "leads" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "email" VARCHAR(100)  UNIQUE,
    "work_email" VARCHAR(100)  UNIQUE,
    "first_name" VARCHAR(100) NOT NULL,
    "last_name" VARCHAR(255) NOT NULL,
    "job_title" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "work_email_status" VARCHAR(20),
    "work_email_quality" VARCHAR(20),
    "work_email_confidence" VARCHAR(20),
    "primary_work_email_source" VARCHAR(100),
    "work_email_service_provider" VARCHAR(100),
    "catch_all_status" BOOL   DEFAULT False,
    "person_address" VARCHAR(255),
    "country" VARCHAR(100),
    "personal_linkedin" VARCHAR(255),
    "seniority" VARCHAR(255),
    "departments" VARCHAR(255),
    "industries" VARCHAR(255),
    "profile_summary" TEXT,
    "company_id" INT REFERENCES "compaies" ("id") ON DELETE SET NULL,
    "created_by_id" INT REFERENCES "users" ("id") ON DELETE SET NULL,
    "updated_by_id" INT REFERENCES "users" ("id") ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
