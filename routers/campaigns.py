from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Campaign, CommentLog, DMLog, Material
from models.user import User
from schemas.campaign import CampaignCreate, CampaignOut, CampaignUpdate

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def _campaign_to_out(campaign: Campaign, db: Session) -> dict:
    total_comments = db.query(CommentLog).filter(CommentLog.campaign_id == campaign.id).count()
    total_dms_sent = db.query(DMLog).filter(DMLog.campaign_id == campaign.id, DMLog.status == "sent").count()
    return {
        **{c.key: getattr(campaign, c.key) for c in campaign.__table__.columns},
        "materials": campaign.materials,
        "total_comments": total_comments,
        "total_dms_sent": total_dms_sent,
    }


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaigns = db.query(Campaign).filter(Campaign.user_id == user.id).order_by(Campaign.created_at.desc()).all()
    return [_campaign_to_out(c, db) for c in campaigns]


@router.post("", response_model=CampaignOut)
async def create_campaign(data: CampaignCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = Campaign(
        user_id=user.id,
        platform=data.platform,
        post_id=data.post_id,
        post_url=data.post_url,
        keyword=data.keyword.lower(),
    )
    db.add(campaign)
    db.flush()

    for mat in data.materials:
        db.add(Material(campaign_id=campaign.id, material_type=mat.material_type, content=mat.content, order=mat.order))

    db.commit()
    db.refresh(campaign)
    return _campaign_to_out(campaign, db)


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(campaign_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == user.id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign_to_out(campaign, db)


@router.put("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: int, data: CampaignUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == user.id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if data.keyword is not None:
        campaign.keyword = data.keyword.lower()
    if data.is_active is not None:
        campaign.is_active = data.is_active
    if data.post_url is not None:
        campaign.post_url = data.post_url

    if data.materials is not None:
        # Replace all materials
        db.query(Material).filter(Material.campaign_id == campaign.id).delete()
        for mat in data.materials:
            db.add(Material(campaign_id=campaign.id, material_type=mat.material_type, content=mat.content, order=mat.order))

    db.commit()
    db.refresh(campaign)
    return _campaign_to_out(campaign, db)


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == user.id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    db.delete(campaign)
    db.commit()
    return {"detail": "Campaign deleted"}
