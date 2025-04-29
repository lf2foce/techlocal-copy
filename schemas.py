from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, List, Dict, Union
from datetime import date, datetime
import json


from enum import Enum

class ContentType(BaseModel):
    platform: str
    topicStyle: str
    suggestedContentTypes: list[str]

class CampaignData(BaseModel):
    mindset: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    targetCustomer: Optional[str] = None
    insight: Optional[str] = None
    brandPersona: Optional[str] = None
    campaignObjective: Optional[Literal["Connect", "Educate", "Inspire", "Promote", "Entertain", "Engage"]] = None
    purposeGoal: Optional[Literal["Inspire", "Convert", "Teach", "Make Laugh"]] = None
    topicStyle: Optional[Literal["Motivational", "Educational", "Storytelling", "Product-Driven", "Emotional", "How-To"]] = None
    brandVoice: Optional[str] = None
    toneWriting: Optional[str] = None
    keyMessages: Optional[list[str]] = None
    painPoints: Optional[list[str]] = None
    bigKeywords: Optional[list[str]] = None
    platforms: Optional[list[str]] = None
    contentTypes: Optional[list[ContentType]] = None
    callsToAction: Optional[list[str]] = None
    imageMood: Optional[str] = None
    confidenceScore: Optional[int] = Field(None, ge=0, le=100)

class CampaignBase(BaseModel):
    title: str
    repeat_every_days: int = Field(..., gt=0)
    target_customer: Optional[str] = None
    insight: Optional[str] = None
    description: Optional[str] = None
    current_step: int = Field(default=1)
    campaign_data: Optional[CampaignData] = None

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

class ContentItem(BaseModel):
    goal: str
    title: str
    format: str
    content_idea: str

class Plan(BaseModel):
    items: List[ContentItem]

class ThemeBase(BaseModel):
    title: str
    story: Optional[str] = None
    content_plan: Optional[Plan] = None 

class ThemeResponse(ThemeBase):
    id: int
    campaign_id: int
    is_selected: bool
    status: str
    post_status: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class PostMetadata(BaseModel):
    content_type: Optional[str] = None
    content_ideas: Optional[str] = None
    goals: Optional[str] = None
    content_length: Optional[int] = None

class ContentPostResponse(BaseModel):
    id: int
    campaign_id: int
    theme_id: int
    title: Optional[str] = None
    content: str
    status: str
    created_at: Optional[datetime] = None
    scheduled_date: Optional[date]
    posted_at: Optional[datetime]
    feedback: Optional[str]
    image_url: Optional[str]
    video_url: Optional[str]
    post_metadata: Optional[PostMetadata] = None

    class Config:
        from_attributes = True
