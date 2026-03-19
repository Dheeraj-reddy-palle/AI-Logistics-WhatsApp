from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.booking import Booking
from app.models.driver import Driver
from app.ai.state_machine import StateMachine
from app.config.settings import settings

router = APIRouter()
state_manager = StateMachine(redis_url=settings.REDIS_URL)

def serialize_model(model_instance):
    """Serialize SQLAlchemy model instances safely by stripping private state keys."""
    return {k: v for k, v in model_instance.__dict__.items() if not k.startswith("_")}

@router.get("/bookings")
async def get_bookings(db: AsyncSession = Depends(get_db)):
    """Fetch all bookings ordered by latest first."""
    try:
        result = await db.execute(select(Booking).order_by(Booking.created_at.desc()))
        return [serialize_model(b) for b in result.scalars().all()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/drivers")
async def get_drivers(db: AsyncSession = Depends(get_db)):
    """Fetch all active and inactive drivers."""
    try:
        result = await db.execute(select(Driver))
        return [serialize_model(d) for d in result.scalars().all()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/state/{phone}")
async def get_state(phone: str):
    """Fetch the active conversational context dictionary from Redis for a target user."""
    try:
        state = await state_manager.get_state(phone)
        return state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
