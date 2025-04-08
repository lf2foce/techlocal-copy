from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date, datetime

from enum import Enum

class CampaignBase(BaseModel):
    title: str
    repeat_every_days: int = Field(..., gt=0)
    target_customer: Optional[str] = None
    insight: Optional[str] = None
    description: Optional[str] = None
    current_step: int = Field(default=1)

class CampaignCreate(CampaignBase):
    pass

class CampaignResponse(CampaignBase):
    id: int
    is_active: bool
    start_date: Optional[date]
    last_run_date: Optional[date]
    next_run_date: Optional[date]
    current_step: int

    class Config:
        from_attributes = True
        use_enum_values = True

class ThemeBase(BaseModel):
    title: str
    story: Optional[str] = None

class ThemeResponse(ThemeBase):
    id: int
    campaign_id: int
    is_selected: bool
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class ContentPostResponse(BaseModel):
    id: int
    campaign_id: int
    theme_id: int
    title: Optional[str] = None
    content: str
    status: str
    created_at: datetime
    scheduled_date: Optional[date]
    posted_at: Optional[datetime]
    feedback: Optional[str]
    image_url: Optional[str]
    video_url: Optional[str]

    class Config:
        from_attributes = True
