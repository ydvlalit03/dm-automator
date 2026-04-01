from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from models import Campaign, CommentLog, DMLog

LINKEDIN_API_URL = "https://api.linkedin.com/rest"


async def fetch_post_comments(post_urn: str, access_token: str) -> list[dict]:
    """Fetch comments on a LinkedIn post."""
    encoded_urn = post_urn.replace(":", "%3A")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Linkedin-Version": "202603",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    comments = []
    start = 0
    count = 50

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            resp = await client.get(
                f"{LINKEDIN_API_URL}/socialActions/{encoded_urn}/comments",
                headers=headers,
                params={"start": start, "count": count},
            )
            if resp.status_code != 200:
                break

            data = resp.json()
            elements = data.get("elements", [])
            comments.extend(elements)

            if len(elements) < count:
                break
            start += count

    return comments


async def reply_to_comment(
    post_urn: str,
    comment_urn: str,
    org_urn: str,
    access_token: str,
    message: str,
) -> dict:
    """Reply to a LinkedIn comment with a message (e.g., material link)."""
    encoded_post_urn = post_urn.replace(":", "%3A")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Linkedin-Version": "202603",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }

    body = {
        "actor": org_urn,
        "object": post_urn,
        "message": {"text": message},
        "parentComment": comment_urn,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{LINKEDIN_API_URL}/socialActions/{encoded_post_urn}/comments",
            headers=headers,
            json=body,
        )
        return {"status_code": resp.status_code, "body": resp.json()}


async def process_linkedin_comments(db: Session, campaign: Campaign, access_token: str):
    """Poll and process comments for a LinkedIn campaign."""
    from services.keyword_matcher import matches

    comments = await fetch_post_comments(campaign.post_id, access_token)

    for comment in comments:
        comment_id = comment.get("$URN", comment.get("commentUrn", ""))
        if not comment_id:
            continue

        message_text = comment.get("message", {}).get("text", "")
        actor = comment.get("actor", "")

        if not matches(message_text, campaign.keyword):
            continue

        # Dedup
        existing = db.query(CommentLog).filter(CommentLog.comment_id == comment_id).first()
        if existing:
            continue

        commenter_username = actor.split(":")[-1] if actor else None

        comment_log = CommentLog(
            campaign_id=campaign.id,
            platform="linkedin",
            comment_id=comment_id,
            commenter_platform_id=actor,
            commenter_username=commenter_username,
            comment_text=message_text,
        )
        db.add(comment_log)
        db.flush()

        # LinkedIn = pending manual DM
        dm_log = DMLog(
            comment_log_id=comment_log.id,
            campaign_id=campaign.id,
            platform="linkedin",
            recipient_platform_id=actor,
            status="pending_manual",
        )
        db.add(dm_log)

    db.commit()
