from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Campaign, CommentLog, DMLog
from models.user import User

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaigns = db.query(Campaign).filter(Campaign.user_id == user.id).all()
    total = len(campaigns)
    active = sum(1 for c in campaigns if c.is_active)
    ig = sum(1 for c in campaigns if c.platform == "instagram")
    li = sum(1 for c in campaigns if c.platform == "linkedin")

    campaign_ids = [c.id for c in campaigns]
    total_comments = db.query(CommentLog).filter(CommentLog.campaign_id.in_(campaign_ids)).count() if campaign_ids else 0
    total_sent = db.query(DMLog).filter(DMLog.campaign_id.in_(campaign_ids), DMLog.status == "sent").count() if campaign_ids else 0
    total_failed = db.query(DMLog).filter(DMLog.campaign_id.in_(campaign_ids), DMLog.status == "failed").count() if campaign_ids else 0
    total_pending = db.query(DMLog).filter(DMLog.campaign_id.in_(campaign_ids), DMLog.status == "pending_manual").count() if campaign_ids else 0

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "stats": {
            "total_campaigns": total,
            "active_campaigns": active,
            "ig_campaigns": ig,
            "linkedin_campaigns": li,
            "total_comments": total_comments,
            "total_dms_sent": total_sent,
            "total_dms_failed": total_failed,
            "total_pending_manual": total_pending,
        },
    })


@router.get("/dashboard/campaigns", response_class=HTMLResponse)
async def campaign_list(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
async def campaign_create_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("campaigns/create.html", {"request": request, "user": user})


@router.get("/dashboard/campaigns/{campaign_id}", response_class=HTMLResponse)
async def campaign_detail(
    campaign_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == user.id).first()
    if not campaign:
        return RedirectResponse(url="/dashboard/campaigns", status_code=303)

    comment_logs = (
        db.query(CommentLog).filter(CommentLog.campaign_id == campaign.id).order_by(CommentLog.detected_at.desc()).limit(100).all()
    )
    dm_logs = (
        db.query(DMLog).filter(DMLog.campaign_id == campaign.id).order_by(DMLog.created_at.desc()).limit(100).all()
    )
    stats = {
        "total_comments": db.query(CommentLog).filter(CommentLog.campaign_id == campaign.id).count(),
        "total_sent": db.query(DMLog).filter(DMLog.campaign_id == campaign.id, DMLog.status == "sent").count(),
        "total_failed": db.query(DMLog).filter(DMLog.campaign_id == campaign.id, DMLog.status == "failed").count(),
        "total_pending": db.query(DMLog).filter(DMLog.campaign_id == campaign.id, DMLog.status == "pending_manual").count(),
        "total_skipped": db.query(DMLog).filter(DMLog.campaign_id == campaign.id, DMLog.status == "skipped_24h").count(),
    }

    return templates.TemplateResponse("campaigns/detail.html", {
        "request": request,
        "user": user,
        "campaign": campaign,
        "comment_logs": comment_logs,
        "dm_logs": dm_logs,
        "stats": stats,
    })


@router.get("/dashboard/linkedin/pending", response_class=HTMLResponse)
async def linkedin_pending(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
    return templates.TemplateResponse("settings.html", {"request": request, "user": user})


@router.post("/dashboard/settings")
async def update_settings(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    form = await request.form()

    user.ig_business_account_id = form.get("ig_business_account_id", "").strip() or None
    user.ig_page_access_token = form.get("ig_page_access_token", "").strip() or None
    user.linkedin_org_urn = form.get("linkedin_org_urn", "").strip() or None
    user.linkedin_access_token = form.get("linkedin_access_token", "").strip() or None

    db.commit()
    return RedirectResponse(url="/dashboard/settings", status_code=303)
