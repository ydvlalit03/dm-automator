from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), default="")

    # Instagram
    ig_business_account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ig_page_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    # LinkedIn
    linkedin_org_urn: Mapped[str | None] = mapped_column(String(150), nullable=True)
    linkedin_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="user")
