from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "stages" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "lead_id_id" INT REFERENCES "leads" ("id") ON DELETE SET NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "stages";"""
