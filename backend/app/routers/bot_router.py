from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import BotUser

router = APIRouter(prefix="/api/bot", tags=["bot"])


class AddUserRequest(BaseModel):
    telegram_id: int
    display_name: str | None = None
    added_by_telegram_id: int | None = None


@router.get("/users/{telegram_id}")
async def check_user(telegram_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(BotUser, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    return {"telegram_id": user.telegram_id, "display_name": user.display_name}


@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    users = (await db.execute(select(BotUser).order_by(BotUser.added_at))).scalars().all()
    return [{"telegram_id": u.telegram_id, "display_name": u.display_name, "added_at": u.added_at} for u in users]


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def add_user(body: AddUserRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.get(BotUser, body.telegram_id)
    if existing:
        raise HTTPException(status_code=409, detail="Already exists")
    user = BotUser(
        telegram_id=body.telegram_id,
        display_name=body.display_name,
        added_by_telegram_id=body.added_by_telegram_id,
    )
    db.add(user)
    await db.commit()
    return {"telegram_id": user.telegram_id}


@router.delete("/users/{telegram_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(telegram_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(BotUser, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(user)
    await db.commit()
