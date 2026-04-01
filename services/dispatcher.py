from sqlalchemy.orm import Session

from models import Campaign
from services import keyword_matcher
from services.instagram import process_comment_event


async def dispatch_instagram_comment(
    db: Session,
    media_id: str,
    comment_id: str,
    comment_text: str,
    commenter_id: str,
    commenter_username: str | None,
):
    """Find matching campaigns for an IG comment and process them."""
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

        user = campaign.user
        ig_business_id = user.ig_business_account_id
        access_token = user.ig_page_access_token

        if not ig_business_id or not access_token:
            continue

        await process_comment_event(
            db=db,
            campaign=campaign,
            comment_id=comment_id,
            commenter_id=commenter_id,
            commenter_username=commenter_username,
            comment_text=comment_text,
            ig_business_id=ig_business_id,
            access_token=access_token,
        )
