import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Media, MediaCategory, MediaType, WatchedStatus
from app.schemas import MediaCreate, MediaListResponse, MediaResponse, MediaUpdate, StatsResponse

router = APIRouter(prefix="/api/media", tags=["media"])
stats_router = APIRouter(prefix="/api", tags=["stats"])


@router.get("", response_model=MediaListResponse)
async def list_media(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: MediaCategory | None = None,
    type: MediaType | None = None,
    watched_status: WatchedStatus | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    q = select(Media)
    if category:
        q = q.where(Media.category == category)
    if type:
        q = q.where(Media.type == type)
    if watched_status:
        q = q.where(Media.watched_status == watched_status)
    if search:
        pattern = f"%{search}%"
        q = q.where(Media.title.ilike(pattern) | Media.title_ru.ilike(pattern))

    total_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(total_q)).scalar_one()

    q = q.order_by(Media.added_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(q)).scalars().all()
    return MediaListResponse(items=items, total=total, page=page, page_size=page_size)


# /random MUST be before /{media_id} so FastAPI doesn't treat "random" as a UUID
@router.get("/random", response_model=MediaResponse)
async def random_media(
    category: MediaCategory | None = None,
    type: MediaType | None = None,
    watched_status: WatchedStatus | None = None,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    q = select(Media)
    if category:
        q = q.where(Media.category == category)
    if type:
        q = q.where(Media.type == type)
    if watched_status:
        q = q.where(Media.watched_status == watched_status)
    q = q.order_by(func.random()).limit(1)
    result = (await db.execute(q)).scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404, detail="No media found")
    return result


@stats_router.get("/stats", response_model=StatsResponse)
async def stats(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    total = (await db.execute(select(func.count(Media.id)))).scalar_one()

    by_type: dict[str, int] = {}
    for row in (await db.execute(select(Media.type, func.count()).group_by(Media.type))).all():
        by_type[row[0].value] = row[1]

    by_category: dict[str, int] = {}
    for row in (await db.execute(select(Media.category, func.count()).group_by(Media.category))).all():
        by_category[row[0].value] = row[1]

    by_watched: dict[str, int] = {}
    for row in (await db.execute(select(Media.watched_status, func.count()).group_by(Media.watched_status))).all():
        by_watched[row[0].value] = row[1]

    return StatsResponse(total=total, by_type=by_type, by_category=by_category, by_watched_status=by_watched)


@router.post("", response_model=MediaResponse, status_code=status.HTTP_201_CREATED)
async def create_media(
    body: MediaCreate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    media = Media(**body.model_dump())
    db.add(media)
    await db.commit()
    await db.refresh(media)
    return media


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media(
    media_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Not found")
    return media


@router.patch("/{media_id}", response_model=MediaResponse)
async def patch_media(
    media_id: uuid.UUID,
    body: MediaUpdate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(media, field, value)
    await db.commit()
    await db.refresh(media)
    return media


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    media_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(media)
    await db.commit()
