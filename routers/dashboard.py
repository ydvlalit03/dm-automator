from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Campaign, CommentLog, DMLog, DMQueue
from models.instagram_post import InstagramPost
from models.user import User

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="templates")

DM_DAILY_LIMIT = 200


@router.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if isinstance(user, RedirectResponse):
        return user

    campaigns = db.query(Campaign).filter(Campaign.user_id == user.id).all()
    campaign_ids = [c.id for c in campaigns]
    active = sum(1 for c in campaigns if c.is_active)
    tracked_posts = db.query(InstagramPost).filter(InstagramPost.user_id == user.id, InstagramPost.status == "active").count()

    total_comments = db.query(CommentLog).filter(CommentLog.campaign_id.in_(campaign_ids)).count() if campaign_ids else 0
    total_sent = db.query(DMLog).filter(DMLog.campaign_id.in_(campaign_ids), DMLog.status == "sent").count() if campaign_ids else 0
    total_failed = db.query(DMLog).filter(DMLog.campaign_id.in_(campaign_ids), DMLog.status == "failed").count() if campaign_ids else 0
    queued_dms = db.query(DMQueue).filter(DMQueue.status == "queued").count()

    # Today's DM count for rate limit
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    dms_sent_today = db.query(DMLog).filter(DMLog.status == "sent", DMLog.sent_at >= today_start).count()
    rate_limit_pct = min(100, int((dms_sent_today / DM_DAILY_LIMIT) * 100))

    # Recent activity
    recent_dms = (
        db.query(DMLog)
        .filter(DMLog.campaign_id.in_(campaign_ids))
        .order_by(DMLog.created_at.desc())
        .limit(20)
        .all()
    ) if campaign_ids else []

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "stats": {
            "active_campaigns": active,
            "tracked_posts": tracked_posts,
            "total_comments": total_comments,
            "total_dms_sent": total_sent,
            "total_dms_failed": total_failed,
            "queued_dms": queued_dms,
            "dms_sent_today": dms_sent_today,
            "dm_daily_limit": DM_DAILY_LIMIT,
            "rate_limit_pct": rate_limit_pct,
        },
        "recent_dms": recent_dms,
    })


@router.get("/dashboard/campaigns", response_class=HTMLResponse)
async def campaign_list(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if isinstance(user, RedirectResponse):
        return user

    campaigns = db.query(Campaign).filter(Campaign.user_id == user.id).order_by(Campaign.created_at.desc()).all()
    campaign_data = []
    for c in campaigns:
        dms_sent = db.query(DMLog).filter(DMLog.campaign_id == c.id, DMLog.status == "sent").count()
        comments = db.query(CommentLog).filter(CommentLog.campaign_id == c.id).count()
        campaign_data.append({"campaign": c, "dms_sent": dms_sent, "comments": comments})

    return templates.TemplateResponse("campaigns/list.html", {
        "request": request,
        "user": user,
        "campaign_data": campaign_data,
    })


@router.get("/dashboard/campaigns/new", response_class=HTMLResponse)
async def campaign_create_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if isinstance(user, RedirectResponse):
        return user

    posts = (
        db.query(InstagramPost)
        .filter(InstagramPost.user_id == user.id, InstagramPost.status == "active", InstagramPost.media_id != None)
        .order_by(InstagramPost.created_at.desc())
        .all()
    )
    return templates.TemplateResponse("campaigns/create.html", {"request": request, "user": user, "posts": posts})


@router.get("/dashboard/campaigns/{campaign_id}", response_class=HTMLResponse)
async def campaign_detail(
    campaign_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if isinstance(user, RedirectResponse):
        return user

    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == user.id).first()
    if not campaign:
        return RedirectResponse(url="/dashboard/campaigns", status_code=303)

    comment_logs = (
        db.query(CommentLog).filter(CommentLog.campaign_id == campaign.id).order_by(CommentLog.detected_at.desc()).limit(100).all()
    )
    dm_logs = (
        db.query(DMLog).filter(DMLog.campaign_id == campaign.id).order_by(DMLog.created_at.desc()).limit(100).all()
    )
    queued = db.query(DMQueue).filter(DMQueue.campaign_id == campaign.id, DMQueue.status == "queued").count()
    stats = {
        "total_comments": db.query(CommentLog).filter(CommentLog.campaign_id == campaign.id).count(),
        "total_sent": db.query(DMLog).filter(DMLog.campaign_id == campaign.id, DMLog.status == "sent").count(),
        "total_failed": db.query(DMLog).filter(DMLog.campaign_id == campaign.id, DMLog.status == "failed").count(),
        "total_skipped": db.query(DMLog).filter(DMLog.campaign_id == campaign.id, DMLog.status == "skipped_24h").count(),
        "queued": queued,
    }

    return templates.TemplateResponse("campaigns/detail.html", {
        "request": request,
        "user": user,
        "campaign": campaign,
        "comment_logs": comment_logs,
        "dm_logs": dm_logs,
        "stats": stats,
    })


@router.get("/dashboard/queue", response_class=HTMLResponse)
async def queue_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if isinstance(user, RedirectResponse):
        return user

    campaign_ids = [c.id for c in db.query(Campaign).filter(Campaign.user_id == user.id).all()]

    queued = (
        db.query(DMQueue)
        .filter(DMQueue.campaign_id.in_(campaign_ids))
        .order_by(DMQueue.created_at.desc())
        .limit(100)
        .all()
    ) if campaign_ids else []

    return templates.TemplateResponse("queue.html", {"request": request, "user": user, "queue_items": queued})


@router.get("/dashboard/linkedin/pending", response_class=HTMLResponse)
async def linkedin_pending(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if isinstance(user, RedirectResponse):
        return user

    pending = (
        db.query(DMLog)
        .join(Campaign)
        .filter(Campaign.user_id == user.id, DMLog.platform == "linkedin", DMLog.status == "pending_manual")
        .order_by(DMLog.created_at.desc())
        .all()
    )

    return templates.TemplateResponse("linkedin/pending_dms.html", {
        "request": request,
        "user": user,
        "pending_dms": pending,
    })


@router.get("/dashboard/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: User = Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse("settings.html", {"request": request, "user": user})


@router.post("/dashboard/settings")
async def update_settings(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if isinstance(user, RedirectResponse):
        return user

    form = await request.form()

    user.ig_business_account_id = form.get("ig_business_account_id", "").strip() or None
    user.ig_page_access_token = form.get("ig_page_access_token", "").strip() or None
    user.linkedin_org_urn = form.get("linkedin_org_urn", "").strip() or None
    user.linkedin_access_token = form.get("linkedin_access_token", "").strip() or None

    db.commit()
    return RedirectResponse(url="/dashboard/settings", status_code=303)
