from fastapi import APIRouter, BackgroundTasks, Request
from starlette.responses import PlainTextResponse

from config import settings
from database import SessionLocal
from services.dispatcher import dispatch_instagram_comment
from services.instagram import verify_signature

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/instagram")
async def instagram_verify(request: Request):
    """Meta webhook verification challenge."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.WEBHOOK_VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)

    return PlainTextResponse(content="Forbidden", status_code=403)


async def _process_ig_webhook(payload: dict):
    """Background task to process Instagram webhook events."""
    db = SessionLocal()
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") != "comments":
                    continue

                value = change.get("value", {})
                media_id = value.get("media", {}).get("id", "")
                comment_id = value.get("id", "")
                comment_text = value.get("text", "")
                from_user = value.get("from", {})
                commenter_id = from_user.get("id", "")
                commenter_username = from_user.get("username")

                if not media_id or not comment_id or not comment_text:
                    continue

                await dispatch_instagram_comment(
                    db=db,
                    media_id=media_id,
                    comment_id=comment_id,
                    comment_text=comment_text,
                    commenter_id=commenter_id,
                    commenter_username=commenter_username,
                )
    finally:
        db.close()


@router.post("/instagram")
async def instagram_receive(request: Request, background_tasks: BackgroundTasks):
    """Receive Instagram webhook events. Returns 200 immediately, processes in background."""
    body = await request.body()

    # Validate signature if META_APP_SECRET is configured
    if settings.META_APP_SECRET:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not verify_signature(body, signature, settings.META_APP_SECRET):
            return PlainTextResponse(content="OK", status_code=200)

    payload = await request.json()

    if payload.get("object") == "instagram":
        background_tasks.add_task(_process_ig_webhook, payload)

    return PlainTextResponse(content="OK", status_code=200)
