import asyncio
import logging

from database import SessionLocal
from models import Campaign
from models.user import User
from services.linkedin import process_linkedin_comments

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 300  # 5 minutes


async def linkedin_poll_loop():
    """Background task that polls LinkedIn comments for all active LinkedIn campaigns."""
    logger.info("LinkedIn poller started (interval: %ds)", POLL_INTERVAL_SECONDS)

    while True:
        try:
            await _poll_all()
        except Exception:
            logger.exception("Error in LinkedIn poll cycle")

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _poll_all():
    db = SessionLocal()
    try:
        campaigns = (
            db.query(Campaign)
            .filter(Campaign.platform == "linkedin", Campaign.is_active == True)
            .all()
        )

        for campaign in campaigns:
            user = campaign.user
            if not user.linkedin_access_token:
                continue

            try:
                await process_linkedin_comments(db, campaign, user.linkedin_access_token)
                logger.info("Polled LinkedIn campaign %d (%s)", campaign.id, campaign.keyword)
            except Exception:
                logger.exception("Error polling campaign %d", campaign.id)
    finally:
        db.close()
