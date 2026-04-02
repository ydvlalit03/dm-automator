import asyncio
import logging
from datetime import UTC, datetime, timedelta

from database import SessionLocal
from models import Campaign, CommentLog, DMLog, DMQueue
from models.user import User
from services.instagram import send_dm

logger = logging.getLogger(__name__)

SEND_INTERVAL_SECONDS = 30
MAX_DMS_PER_DAY = 200


async def dm_sender_loop():
    """Background task that processes the DM queue."""
    logger.info("DM sender started (interval: %ds, daily limit: %d)", SEND_INTERVAL_SECONDS, MAX_DMS_PER_DAY)

    while True:
        try:
            await _process_queue()
        except Exception:
            logger.exception("Error in DM sender cycle")

        await asyncio.sleep(SEND_INTERVAL_SECONDS)


async def _process_queue():
    db = SessionLocal()
    try:
        # Check daily rate limit
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        sent_today = (
            db.query(DMLog)
            .filter(DMLog.platform == "instagram", DMLog.status == "sent", DMLog.sent_at >= today_start)
            .count()
        )

        if sent_today >= MAX_DMS_PER_DAY:
            logger.warning("Daily DM limit reached (%d/%d). Queue paused.", sent_today, MAX_DMS_PER_DAY)
            return

        remaining = MAX_DMS_PER_DAY - sent_today

        # Get queued items ready to send
        now = datetime.now(UTC)
        queued_items = (
            db.query(DMQueue)
            .filter(
                DMQueue.status == "queued",
                (DMQueue.next_retry_at == None) | (DMQueue.next_retry_at <= now),
            )
            .order_by(DMQueue.created_at.asc())
            .limit(min(remaining, 10))  # Process max 10 per cycle
            .all()
        )

        for item in queued_items:
            campaign = db.query(Campaign).filter(Campaign.id == item.campaign_id).first()
            if not campaign or not campaign.is_active:
                item.status = "failed"
                item.error_message = "Campaign inactive or deleted"
                db.commit()
                continue

            # Check campaign DM limit
            if campaign.dm_limit and campaign.dm_count >= campaign.dm_limit:
                item.status = "failed"
                item.error_message = "Campaign DM limit reached"
                db.commit()
                continue

            user = campaign.user
            if not user.ig_business_account_id or not user.ig_page_access_token:
                item.status = "failed"
                item.error_message = "Instagram not connected"
                db.commit()
                continue

            item.status = "processing"
            db.commit()

            # Send DM
            try:
                materials = sorted(campaign.materials, key=lambda m: m.order)
                if not materials:
                    item.status = "failed"
                    item.error_message = "No materials in campaign"
                    db.commit()
                    continue

                results = await send_dm(
                    user.ig_business_account_id,
                    user.ig_page_access_token,
                    item.recipient_id,
                    materials,
                )

                all_ok = all(r["status_code"] == 200 for r in results)

                comment_log = db.query(CommentLog).filter(CommentLog.id == item.comment_log_id).first()

                if all_ok:
                    item.status = "sent"

                    # Create DM log
                    dm_log = DMLog(
                        comment_log_id=item.comment_log_id,
                        campaign_id=item.campaign_id,
                        platform="instagram",
                        recipient_platform_id=item.recipient_id,
                        status="sent",
                        sent_at=datetime.now(UTC),
                    )
                    db.add(dm_log)

                    # Increment campaign counter
                    campaign.dm_count += 1

                    logger.info("DM sent to %s for campaign %d", item.recipient_username or item.recipient_id, campaign.id)
                else:
                    errors = [r["body"] for r in results if r["status_code"] != 200]
                    error_str = str(errors)[:500]

                    if "NOT_WITHIN_WINDOW" in error_str or "messaging window" in error_str.lower():
                        # Don't retry — 24h window issue
                        item.status = "failed"
                        item.error_message = "24h messaging window not open"

                        dm_log = DMLog(
                            comment_log_id=item.comment_log_id,
                            campaign_id=item.campaign_id,
                            platform="instagram",
                            recipient_platform_id=item.recipient_id,
                            status="skipped_24h",
                            error_message=error_str,
                        )
                        db.add(dm_log)
                    elif item.retry_count < item.max_retries:
                        # Retry with backoff
                        item.status = "queued"
                        item.retry_count += 1
                        backoff = 60 * (2 ** item.retry_count)  # 2min, 4min, 8min
                        item.next_retry_at = datetime.now(UTC) + timedelta(seconds=backoff)
                        item.error_message = error_str
                        logger.warning("DM failed, retry %d/%d in %ds", item.retry_count, item.max_retries, backoff)
                    else:
                        item.status = "failed"
                        item.error_message = error_str

                        dm_log = DMLog(
                            comment_log_id=item.comment_log_id,
                            campaign_id=item.campaign_id,
                            platform="instagram",
                            recipient_platform_id=item.recipient_id,
                            status="failed",
                            error_message=f"Failed after {item.max_retries} retries: {error_str}",
                        )
                        db.add(dm_log)

                db.commit()

            except Exception as e:
                logger.exception("Error sending DM for queue item %d", item.id)
                if item.retry_count < item.max_retries:
                    item.status = "queued"
                    item.retry_count += 1
                    item.next_retry_at = datetime.now(UTC) + timedelta(seconds=60 * (2 ** item.retry_count))
                    item.error_message = str(e)[:500]
                else:
                    item.status = "failed"
                    item.error_message = str(e)[:500]
                db.commit()

    finally:
        db.close()
