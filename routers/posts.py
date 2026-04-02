from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models.instagram_post import InstagramPost
from models.user import User
from services.url_resolver import bulk_resolve, detect_post_type, extract_shortcode

router = APIRouter(tags=["posts"])
templates = Jinja2Templates(directory="templates")


class BulkAddRequest(BaseModel):
    urls: list[str]


@router.post("/api/posts/bulk-add")
async def bulk_add_posts(data: BulkAddRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Accept a list of Instagram URLs, resolve Media IDs, and save them."""
    if not user.ig_business_account_id or not user.ig_page_access_token:
        raise HTTPException(status_code=400, detail="Instagram not connected. Go to Settings first.")

    # Filter out empty lines
    urls = [u.strip() for u in data.urls if u.strip()]
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided")

    # Resolve all URLs
    resolved = await bulk_resolve(urls, user.ig_business_account_id, user.ig_page_access_token)

    added = []
    errors = []

    for item in resolved:
        if item["error"]:
            errors.append({"url": item["url"], "error": item["error"]})
            continue

        # Check if shortcode already exists
        existing = db.query(InstagramPost).filter(InstagramPost.shortcode == item["shortcode"]).first()
        if existing:
            errors.append({"url": item["url"], "error": "Already tracked"})
            continue

        post = InstagramPost(
            user_id=user.id,
            url=item["url"],
            shortcode=item["shortcode"],
            media_id=item["media_id"],
            caption=(item["caption"] or "")[:500],
            post_type=item["post_type"],
            status="active",
        )
        db.add(post)
        added.append({"url": item["url"], "shortcode": item["shortcode"], "media_id": item["media_id"]})

    db.commit()

    return {"added": added, "errors": errors, "total_added": len(added), "total_errors": len(errors)}


@router.get("/api/posts")
async def list_posts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all tracked Instagram posts."""
    posts = (
        db.query(InstagramPost)
        .filter(InstagramPost.user_id == user.id)
        .order_by(InstagramPost.created_at.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "url": p.url,
            "shortcode": p.shortcode,
            "media_id": p.media_id,
            "caption": (p.caption or "")[:100],
            "post_type": p.post_type,
            "status": p.status,
            "campaign_count": len(p.campaigns),
            "created_at": p.created_at,
        }
        for p in posts
    ]


@router.delete("/api/posts/{post_id}")
async def delete_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a tracked post."""
    post = db.query(InstagramPost).filter(InstagramPost.id == post_id, InstagramPost.user_id == user.id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.campaigns:
        raise HTTPException(status_code=400, detail="Cannot delete post with active campaigns. Delete campaigns first.")

    db.delete(post)
    db.commit()
    return {"detail": "Post deleted"}


@router.post("/api/posts/{post_id}/toggle")
async def toggle_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Toggle post status between active and paused."""
    post = db.query(InstagramPost).filter(InstagramPost.id == post_id, InstagramPost.user_id == user.id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = "paused" if post.status == "active" else "active"
    db.commit()
    return {"detail": f"Post is now {post.status}", "status": post.status}


# Dashboard pages

@router.get("/dashboard/posts", response_class=HTMLResponse)
async def posts_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    posts = (
        db.query(InstagramPost)
        .filter(InstagramPost.user_id == user.id)
        .order_by(InstagramPost.created_at.desc())
        .all()
    )
    return templates.TemplateResponse("posts/list.html", {"request": request, "user": user, "posts": posts})


@router.get("/dashboard/posts/add", response_class=HTMLResponse)
async def add_posts_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("posts/add.html", {"request": request, "user": user})
