from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.auth_router import router as auth_router
from app.routers.media_router import router as media_router, stats_router
from app.routers.resolve_router import router as resolve_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: could run alembic upgrade head here via subprocess in dev
    yield


app = FastAPI(title="Movie Catalog API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Caddy handles real origin restriction
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(media_router)
app.include_router(stats_router)
app.include_router(resolve_router)
