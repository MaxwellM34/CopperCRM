from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DO $$
        BEGIN
            IF to_regclass('public.companies') IS NOT NULL THEN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='companies' AND column_name='lastest_funding_date'
                ) AND NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='companies' AND column_name='latest_funding_date'
                ) THEN
                    ALTER TABLE "companies" RENAME COLUMN "lastest_funding_date" TO "latest_funding_date";
                END IF;
            END IF;
        END $$;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DO $$
        BEGIN
            IF to_regclass('public.companies') IS NOT NULL THEN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='companies' AND column_name='latest_funding_date'
                ) AND NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='companies' AND column_name='lastest_funding_date'
                ) THEN
                    ALTER TABLE "companies" RENAME COLUMN "latest_funding_date" TO "lastest_funding_date";
                END IF;
            END IF;
        END $$;
    """
