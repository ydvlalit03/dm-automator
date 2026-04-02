import logging

from sqlalchemy.orm import Session

from models import Campaign, CommentLog, DMQueue
from services import keyword_matcher

logger = logging.getLogger(__name__)


async def dispatch_instagram_comment(
    db: Session,
    media_id: str,
    comment_id: str,
    comment_text: str,
    commenter_id: str,
    commenter_username: str | None,
):
    """Find matching campaigns for an IG comment, log it, and queue DMs."""
    campaigns = (
        db.query(Campaign)
        .filter(
            Campaign.platform == "instagram",
            Campaign.post_id == media_id,
            Campaign.is_active == True,
        )
        .all()
    )

    for campaign in campaigns:
        if not keyword_matcher.matches(comment_text, campaign.keyword):
            continue

        # Check DM limit
        if campaign.dm_limit and campaign.dm_count >= campaign.dm_limit:
            logger.info("Campaign %d hit DM limit (%d), skipping", campaign.id, campaign.dm_limit)
            continue

        # Dedup by comment_id
        existing = db.query(CommentLog).filter(CommentLog.comment_id == comment_id).first()
        if existing:
            continue

        # Log the comment
        comment_log = CommentLog(
            campaign_id=campaign.id,
            platform="instagram",
            comment_id=comment_id,
            commenter_platform_id=commenter_id,
            commenter_username=commenter_username,
            comment_text=comment_text,
        )
        db.add(comment_log)
        db.flush()

        # Queue the DM instead of sending directly
        queue_item = DMQueue(
            campaign_id=campaign.id,
            comment_log_id=comment_log.id,
            recipient_id=commenter_id,
            recipient_username=commenter_username,
            status="queued",
        )
        db.add(queue_item)

        logger.info(
            "Queued DM for %s (campaign %d, keyword '%s')",
            commenter_username or commenter_id,
            campaign.id,
            campaign.keyword,
        )

    db.commit()
