from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class CommentLog(Base):
    __tablename__ = "comment_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("campaigns.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    comment_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    commenter_platform_id: Mapped[str] = mapped_column(String(255), nullable=False)
    commenter_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    campaign: Mapped["Campaign"] = relationship(back_populates="comment_logs")
    dm_log: Mapped["DMLog | None"] = relationship(back_populates="comment_log", uselist=False)
