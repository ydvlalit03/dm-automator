from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class DMLog(Base):
    __tablename__ = "dm_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comment_log_id: Mapped[int] = mapped_column(Integer, ForeignKey("comment_logs.id"), nullable=False)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("campaigns.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient_platform_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # sent, failed, pending_manual, skipped_24h
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    comment_log: Mapped["CommentLog"] = relationship(back_populates="dm_log")
    campaign: Mapped["Campaign"] = relationship(back_populates="dm_logs")
