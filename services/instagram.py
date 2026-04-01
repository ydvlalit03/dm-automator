import hashlib
import hmac
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from models import Campaign, CommentLog, DMLog, Material

IG_GRAPH_URL = "https://graph.instagram.com/v21.0"


def verify_signature(payload: bytes, signature: str, app_secret: str) -> bool:
    """Verify the X-Hub-Signature-256 header from Meta webhooks."""
    expected = "sha256=" + hmac.new(
        app_secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def send_dm(
    ig_business_id: str,
    access_token: str,
    recipient_id: str,
    materials: list[Material],
) -> list[dict]:
    """Send DM messages for each material item. Returns list of API results."""
    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        for mat in sorted(materials, key=lambda m: m.order):
            body: dict = {"recipient": {"id": recipient_id}}

            if mat.material_type in ("text", "link"):
                body["message"] = {"text": mat.content}
            elif mat.material_type == "image_url":
                body["message"] = {
                    "attachment": {
                        "type": "image",
                        "payload": {"url": mat.content},
                    }
                }

            resp = await client.post(
                f"{IG_GRAPH_URL}/{ig_business_id}/messages",
                params={"access_token": access_token},
                json=body,
            )
            results.append({"status_code": resp.status_code, "body": resp.json()})
    return results


async def process_comment_event(
    db: Session,
    campaign: Campaign,
    comment_id: str,
    commenter_id: str,
    commenter_username: str | None,
    comment_text: str,
    ig_business_id: str,
    access_token: str,
):
    """Process a matched Instagram comment: log it and attempt to send DM."""
    # Dedup
    existing = db.query(CommentLog).filter(CommentLog.comment_id == comment_id).first()
    if existing:
        return

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

    # Attempt DM
    materials = sorted(campaign.materials, key=lambda m: m.order)
    if not materials:
        return

    try:
        results = await send_dm(ig_business_id, access_token, commenter_id, materials)
        all_ok = all(r["status_code"] == 200 for r in results)

        if all_ok:
            status = "sent"
            error = None
        else:
            errors = [r["body"] for r in results if r["status_code"] != 200]
            # Check for 24h messaging window issue
            error_str = str(errors)
            if "NOT_WITHIN_WINDOW" in error_str or "messaging window" in error_str.lower():
                status = "skipped_24h"
            else:
                status = "failed"
            error = error_str[:1000]
    except Exception as e:
        status = "failed"
        error = str(e)[:1000]

    dm_log = DMLog(
        comment_log_id=comment_log.id,
        campaign_id=campaign.id,
        platform="instagram",
        recipient_platform_id=commenter_id,
        status=status,
        error_message=error if status != "sent" else None,
        sent_at=datetime.utcnow() if status == "sent" else None,
    )
    db.add(dm_log)
    db.commit()
