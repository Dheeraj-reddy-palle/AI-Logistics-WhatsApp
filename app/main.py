from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager

from app.config.settings import settings
from app.api.routes import webhook
from app.api.routes import driver as driver_routes
from app.api.routes import admin as admin_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup – create tables and seed mock drivers in dev mode"""
    from app.db.session import AsyncSessionLocal
    from app.db.base import Base
    from app.db.session import engine

    # Create all tables in ALL environments (needed for fresh Render PostgreSQL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logging.info(">>> [STARTUP] Database tables ensured.")

    # Seed mock drivers only in dev mode
    if settings.ENV == "dev":
        from app.models.driver import Driver, VehicleType
        from sqlalchemy.future import select
        import uuid

        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(select(Driver).limit(1))
                if not result.scalars().first():
                    logging.info(">>> [DEV SEED] Inserting mock drivers into DB.")
                    
                    d1 = Driver(
                        id=uuid.uuid4(), name="Amit-Hyderabad", phone="9991",
                        vehicle_type=VehicleType.TRUCK, is_available=True,
                        last_known_lat=17.3850, last_known_lng=78.4867
                    )
                    d2 = Driver(
                        id=uuid.uuid4(), name="Raju-Secunderabad", phone="9992",
                        vehicle_type=VehicleType.TRUCK, is_available=True,
                        last_known_lat=17.4344, last_known_lng=78.5013
                    )
                    d3 = Driver(
                        id=uuid.uuid4(), name="Charlie-Gachibowli", phone="9993",
                        vehicle_type=VehicleType.VAN, is_available=True,
                        last_known_lat=17.4401, last_known_lng=78.3489
                    )
                    
                    session.add_all([d1, d2, d3])
                    await session.commit()
                    logging.info(">>> [DEV SEED] Mock drivers inserted successfully.")
            except Exception as e:
                logging.error(f"Failed to seed drivers: {e}")

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Powered WhatsApp Logistics System — Local Free Mode",
    version="2.0.0",
    lifespan=lifespan
)

# CORS (allow all for local testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routes
app.include_router(webhook.router, prefix="/api/v1")
app.include_router(driver_routes.router, prefix="/api/v1")
app.include_router(admin_routes.router, prefix="/api/v1")

@app.get("/")
async def root_health():
    """Render/Cloud Port health check"""
    return "API running"

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": "2.0.0"}
