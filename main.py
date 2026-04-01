import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from auth import hash_password
from config import settings
from database import Base, SessionLocal, engine
from models import Campaign, CommentLog, DMLog, Material
from models.user import User
from routers import auth_routes, campaigns, dashboard, linkedin_admin, webhooks
from tasks.linkedin_poller import linkedin_poll_loop

logging.basicConfig(level=logging.INFO)
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

    # Start LinkedIn poller
    poller_task = asyncio.create_task(linkedin_poll_loop())
    logger.info("Application started")

    yield

    # Shutdown
    poller_task.cancel()
    try:
        await poller_task
    except asyncio.CancelledError:
        pass
    logger.info("Application stopped")


app = FastAPI(title="DM Automator", lifespan=lifespan)

# Middleware
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(webhooks.router)
app.include_router(auth_routes.router)
app.include_router(campaigns.router)
app.include_router(linkedin_admin.router)
app.include_router(dashboard.router)
