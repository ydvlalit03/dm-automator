from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    instagram_post_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("instagram_posts.id"), nullable=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # "instagram" or "linkedin"
    post_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Media ID for webhook matching
    post_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    keyword: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    dm_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # optional max DMs
    dm_count: Mapped[int] = mapped_column(Integer, default=0)  # DMs sent so far
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="campaigns")
    instagram_post: Mapped["InstagramPost | None"] = relationship(back_populates="campaigns")
    materials: Mapped[list["Material"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    comment_logs: Mapped[list["CommentLog"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    dm_logs: Mapped[list["DMLog"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
