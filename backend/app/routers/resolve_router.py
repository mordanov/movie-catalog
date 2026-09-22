import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    CartoonSubtype,
    Media,
    MediaCategory,
    MediaSource,
    MediaType,
    WatchedStatus,
)
from app.schemas import CandidateResponse, MediaResponse
from app.services.openai_client import (
    classify_media,
    extract_from_screenshot,
    generate_disambiguation_question,
    translate_to_russian,
)
from app.services.storage import upload_poster
from app.services.tmdb import get_details, search_multi

router = APIRouter(tags=["resolve"])


class ResolveRequest(BaseModel):
    query: str


class ConfirmRequest(BaseModel):
    tmdb_id: int
    media_type: str  # "movie" or "tv"
    category: MediaCategory
    cartoon_subtype: CartoonSubtype | None = None
    source: MediaSource
    added_by: str | None = None
    notes: str | None = None


@router.post("/api/resolve", response_model=list[CandidateResponse])
async def resolve(
    body: ResolveRequest,
    _user: str = Depends(get_current_user),
):
    candidates = await search_multi(body.query, language="ru-RU")
    if not candidates:
        candidates = await search_multi(body.query, language="en-US")

    if not candidates:
        return []

    disambiguation_question = None
    if len(candidates) == 1:
        c = candidates[0]
        classification = await classify_media(
            c["title"], c.get("genres", []), c.get("description"), []
        )
        c["category"] = classification.get("category")
        c["cartoon_subtype"] = classification.get("cartoon_subtype")
    else:
        disambiguation_question = await generate_disambiguation_question(candidates[:5])

    return [
        CandidateResponse(
            tmdb_id=c["tmdb_id"],
            media_type=c["media_type"],
            title=c["title"],
            title_ru=None,
            year=c.get("year"),
            description=c.get("description"),
            poster_url=c.get("poster_url"),
            genres=c.get("genres", []),
            rating=c.get("rating"),
            disambiguation_question=disambiguation_question
            if len(candidates) > 1
            else None,
        )
        for c in candidates[:5]
    ]


@router.post("/api/resolve/screenshot", response_model=list[CandidateResponse])
async def resolve_screenshot(
    file: UploadFile = File(...),
    _user: str = Depends(get_current_user),
):
    image_bytes = await file.read()
    extracted = await extract_from_screenshot(image_bytes)
    title = extracted.get("title", "")
    if not title:
        raise HTTPException(
            status_code=422, detail="Could not extract title from screenshot"
        )

    candidates = await search_multi(title, language="ru-RU")
    if not candidates:
        candidates = await search_multi(title, language="en-US")

    disambiguation_question = None
    if len(candidates) > 1:
        disambiguation_question = await generate_disambiguation_question(candidates[:5])

    return [
        CandidateResponse(
            tmdb_id=c["tmdb_id"],
            media_type=c["media_type"],
            title=c["title"],
            title_ru=None,
            year=c.get("year"),
            description=c.get("description"),
            poster_url=c.get("poster_url"),
            genres=c.get("genres", []),
            rating=c.get("rating"),
            disambiguation_question=disambiguation_question,
        )
        for c in candidates[:5]
    ]


@router.post("/api/media/confirm", response_model=MediaResponse, status_code=201)
async def confirm(
    body: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    details = await get_details(body.tmdb_id, body.media_type, language="ru-RU")

    if not details.get("description"):
        details_en = await get_details(body.tmdb_id, body.media_type, language="en-US")
        if details_en.get("description"):
            details["description"] = await translate_to_russian(
                details_en["description"]
            )
        details["title"] = details.get("title") or details_en.get("title", "")

    # R-12: derive MediaType from category, not TMDB media_type
    # (TMDB reports cartoons as "movie"; category field is the source of truth)
    if body.category == MediaCategory.cartoon:
        orm_type = MediaType.cartoon
    elif body.media_type == "tv":
        orm_type = MediaType.series
    else:
        orm_type = MediaType.movie

    poster_url = None
    if details.get("poster_url"):
        filename = f"{body.tmdb_id}_{body.media_type}.jpg"
        poster_url = await upload_poster(details["poster_url"], filename)

    media = Media(
        id=uuid.uuid4(),
        title=details["title"],
        year=details.get("year"),
        description=details.get("description"),
        poster_url=poster_url,
        type=orm_type,
        category=body.category,
        cartoon_subtype=body.cartoon_subtype,
        genres=details.get("genres", []),
        actors=details.get("actors", []),
        external_ids=details.get("external_ids", {"tmdb": body.tmdb_id}),
        rating_external=details.get("rating"),
        watched_status=WatchedStatus.not_watched,
        source=body.source,
        added_by=body.added_by,
        notes=body.notes,
        trailer_url=details.get("trailer_url"),
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)
    return media
