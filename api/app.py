from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from tortoise.contrib.fastapi import register_tortoise
from tortoise import Tortoise
from openai import write_openai_schema 


from config import Config

# routers (adjust names to your project)
# from routers.posts import router as posts_router
# from routers.users import router as users_router


def init_db(app: FastAPI) -> None:
    register_tortoise(
        app,
        config=Config.TORTOISE_ORM,
        generate_schemas=True,          # OK for now; later replace with Aerich migrations
        add_exception_handlers=True,
    )


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # --- startup ---
        #await Tortoise.init(config=Config.TORTOISE_ORM)
        #await Tortoise.generate_schemas(safe=True)  # remove if you only want migrations
        write_openai_schema(app) # later if I want to be doing the thingy thangs with the ai
        print("✅ Generated openai_tools.json")
       

        yield

        # --- shutdown ---
        pass

    app = FastAPI(title="Copper CRM API", lifespan=lifespan)

    # CORS (keep permissive for now; tighten later)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8000",
            "https://crm-api-468831678336.us-central1.run.app"
            # Add your Cloud Run URL later (once created)
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers (uncomment when you have them)
    # app.include_router(users_router)
    # app.include_router(posts_router)

    init_db(app)
    return app
