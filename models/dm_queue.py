from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class DMQueue(Base):
    __tablename__ = "dm_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("campaigns.id"), nullable=False)
    comment_log_id: Mapped[int] = mapped_column(Integer, ForeignKey("comment_logs.id"), nullable=False)
    recipient_id: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued, processing, sent, failed
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
