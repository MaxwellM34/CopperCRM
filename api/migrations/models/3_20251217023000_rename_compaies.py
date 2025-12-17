from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DO $$
        BEGIN
            IF to_regclass('public.compaies') IS NOT NULL THEN
                ALTER TABLE "compaies" RENAME TO "companies";
            END IF;
        END $$;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DO $$
        BEGIN
            IF to_regclass('public.companies') IS NOT NULL AND to_regclass('public.compaies') IS NULL THEN
                ALTER TABLE "companies" RENAME TO "compaies";
            END IF;
        END $$;
    """
