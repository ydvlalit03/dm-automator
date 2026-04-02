import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from auth import hash_password
from config import settings
from database import Base, SessionLocal, engine
from models import Campaign, CommentLog, DMLog, DMQueue, Material
from models.instagram_post import InstagramPost
from models.user import User
from routers import auth_routes, campaigns, dashboard, linkedin_admin, webhooks
from routers.posts import router as posts_router
from tasks.dm_sender import dm_sender_loop
from tasks.linkedin_poller import linkedin_poll_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Seed admin user
    db = SessionLocal()
    try:
        if not db.query(User).first():
            admin = User(
                email=settings.ADMIN_EMAIL,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                display_name="Admin",
                ig_business_account_id=settings.IG_BUSINESS_ACCOUNT_ID or None,
                ig_page_access_token=settings.IG_PAGE_ACCESS_TOKEN or None,
            )
            db.add(admin)
            db.commit()
            logger.info("Admin user created: %s", settings.ADMIN_EMAIL)
    finally:
        db.close()

    # Start background tasks
    dm_task = asyncio.create_task(dm_sender_loop())
    poller_task = asyncio.create_task(linkedin_poll_loop())
    logger.info("Application started")

    yield

    # Shutdown
    dm_task.cancel()
    poller_task.cancel()
    try:
        await dm_task
    except asyncio.CancelledError:
        pass
    try:
        await poller_task
    except asyncio.CancelledError:
        pass
    logger.info("Application stopped")


app = FastAPI(title="DM Automator", lifespan=lifespan)

# Middleware
app.add_middleware(SessionMiddleware, secret_key=settings.get_secret_key())

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(webhooks.router)
app.include_router(auth_routes.router)
app.include_router(campaigns.router)
app.include_router(posts_router)
app.include_router(linkedin_admin.router)
app.include_router(dashboard.router)


# Health check
@app.get("/health")
async def health():
    db = SessionLocal()
    try:
        db.execute(db.bind.raw_connection().cursor().execute("SELECT 1") if False else __import__("sqlalchemy").text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"
    finally:
        db.close()

    # Get queue stats
    db = SessionLocal()
    try:
        queued = db.query(DMQueue).filter(DMQueue.status == "queued").count()
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        sent_today = db.query(DMLog).filter(DMLog.status == "sent", DMLog.sent_at >= today_start).count()
    except Exception:
        queued = -1
        sent_today = -1
    finally:
        db.close()

    return {
        "status": "ok",
        "database": db_status,
        "dm_queue": queued,
        "dms_sent_today": sent_today,
        "dm_daily_limit": settings.DM_RATE_LIMIT_PER_DAY,
    }
