from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class InstagramPost(Base):
    __tablename__ = "instagram_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    shortcode: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    media_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # resolved via Graph API
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    post_type: Mapped[str] = mapped_column(String(20), default="post")  # post, reel, story
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, paused, failed
    resolve_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="instagram_posts")
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="instagram_post")
