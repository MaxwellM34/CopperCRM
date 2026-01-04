from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise

from config import Config
from openai_schema import write_openai_schema
from routers.auth import router as auth_router
from routers.first_emails import router as first_emails_router
from routers.imports import router as leads_router
from routers.users import router as users_router
from routers.approval_stats import router as approval_stats_router
from routers.lead_display import router as lead_display_router
from routers.campaigns import router as campaigns_router
from routers.campaign_runtime import router as campaign_runtime_router
from routers.outbound_inboxes import router as outbound_inboxes_router
from routers.tracking import router as tracking_router
from services.gender_infer import backfill_lead_genders


def init_db(app: FastAPI) -> None:
    register_tortoise(
        app,
        config=Config.TORTOISE_ORM,
        generate_schemas=False,  # OK for now; later replace with Aerich migrations
        add_exception_handlers=True,
    )


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # --- startup ---
        print("Using DB config:", Config.TORTOISE_ORM)
        await Tortoise.init(config=Config.TORTOISE_ORM)

        write_openai_schema(app)  # writes openai_tools.json for tooling
        print("Generated openai_tools.json")
        # Backfill genders for existing leads using the name-based detector
        try:
            updated = await backfill_lead_genders()
            if updated:
                print(f"Updated gender for {updated} leads")
        except Exception as exc:  # noqa: BLE001
            print(f"Gender backfill skipped: {exc}")

        yield

        # --- shutdown ---
        pass

    app = FastAPI(title="Copper CRM API", lifespan=lifespan)

    # CORS (keep permissive for now; tighten later)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "https://crm-api-468831678336.us-central1.run.app",
            "https://crm-frontend-468831678336.us-central1.run.app",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(auth_router)
    app.include_router(leads_router)
    app.include_router(users_router)
    app.include_router(first_emails_router)
    app.include_router(approval_stats_router)
    app.include_router(lead_display_router)
    app.include_router(campaigns_router)
    app.include_router(campaign_runtime_router)
    app.include_router(outbound_inboxes_router)
    app.include_router(tracking_router)

    init_db(app)
    return app
