from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class MaterialCreate(BaseModel):
    material_type: Literal["text", "link", "image_url"]
    content: str
    order: int = 0


class MaterialOut(MaterialCreate):
    id: int
    model_config = {"from_attributes": True}


class CampaignCreate(BaseModel):
    platform: Literal["instagram", "linkedin"]
    post_id: str
    post_url: str | None = None
    instagram_post_id: int | None = None
    keyword: str
    dm_limit: int | None = None
    materials: list[MaterialCreate]


class CampaignUpdate(BaseModel):
    keyword: str | None = None
    post_url: str | None = None
    is_active: bool | None = None
    dm_limit: int | None = None
    materials: list[MaterialCreate] | None = None


class CampaignOut(BaseModel):
    id: int
    platform: str
    post_id: str
    post_url: str | None
    keyword: str
    is_active: bool
    dm_limit: int | None
    dm_count: int
    created_at: datetime
    updated_at: datetime
    materials: list[MaterialOut]
    total_comments: int = 0
    total_dms_sent: int = 0

    model_config = {"from_attributes": True}
