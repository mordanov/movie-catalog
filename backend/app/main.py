from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers.auth_router import router as auth_router
from app.routers.bot_router import router as bot_router
from app.routers.media_router import router as media_router, stats_router
from app.routers.resolve_router import router as resolve_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Movie Catalog API", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(bot_router)
app.include_router(media_router)
app.include_router(stats_router)
app.include_router(resolve_router)
