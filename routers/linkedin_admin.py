from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Campaign, DMLog
from models.user import User
from services.linkedin import process_linkedin_comments, reply_to_comment

router = APIRouter(prefix="/api/linkedin", tags=["linkedin"])


@router.post("/poll-now")
async def trigger_poll(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Manually trigger LinkedIn comment polling for all active campaigns."""
    if not user.linkedin_access_token:
        raise HTTPException(status_code=400, detail="LinkedIn not connected")

    campaigns = (
        db.query(Campaign)
        .filter(Campaign.user_id == user.id, Campaign.platform == "linkedin", Campaign.is_active == True)
        .all()
    )

    processed = 0
    for campaign in campaigns:
        await process_linkedin_comments(db, campaign, user.linkedin_access_token)
        processed += 1

    return {"detail": f"Polled {processed} campaigns"}


@router.get("/pending-dms")
async def list_pending_dms(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all LinkedIn DMs awaiting manual sending."""
    pending = (
        db.query(DMLog)
        .join(Campaign)
        .filter(Campaign.user_id == user.id, DMLog.platform == "linkedin", DMLog.status == "pending_manual")
        .all()
    )

    return [
        {
            "id": dm.id,
            "campaign_keyword": dm.campaign.keyword,
            "recipient_id": dm.recipient_platform_id,
            "comment_text": dm.comment_log.comment_text,
            "commenter_username": dm.comment_log.commenter_username,
            "created_at": dm.created_at,
        }
        for dm in pending
    ]


@router.post("/mark-sent/{log_id}")
async def mark_as_sent(log_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark a pending LinkedIn DM as manually sent."""
    dm = (
        db.query(DMLog)
        .join(Campaign)
        .filter(DMLog.id == log_id, Campaign.user_id == user.id)
        .first()
    )
    if not dm:
        raise HTTPException(status_code=404, detail="DM log not found")

    dm.status = "sent"
    dm.sent_at = datetime.utcnow()
    db.commit()
    return {"detail": "Marked as sent"}


@router.post("/reply-comment/{log_id}")
async def reply_with_material(log_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Auto-reply to a LinkedIn comment with the campaign material link."""
    dm = (
        db.query(DMLog)
        .join(Campaign)
        .filter(DMLog.id == log_id, Campaign.user_id == user.id)
        .first()
    )
    if not dm:
        raise HTTPException(status_code=404, detail="DM log not found")
    if not user.linkedin_access_token or not user.linkedin_org_urn:
        raise HTTPException(status_code=400, detail="LinkedIn not configured")

    campaign = dm.campaign
    materials = sorted(campaign.materials, key=lambda m: m.order)
    material_text = "\n".join(m.content for m in materials)
    message = f"Here's what you requested:\n{material_text}"

    comment_urn = dm.comment_log.comment_id
    result = await reply_to_comment(
        post_urn=campaign.post_id,
        comment_urn=comment_urn,
        org_urn=user.linkedin_org_urn,
        access_token=user.linkedin_access_token,
        message=message,
    )

    if result["status_code"] in (200, 201):
        dm.status = "sent"
        dm.sent_at = datetime.utcnow()
    else:
        dm.status = "failed"
        dm.error_message = str(result["body"])[:1000]

    db.commit()
    return result
