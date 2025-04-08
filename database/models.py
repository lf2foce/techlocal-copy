from sqlalchemy import Column, Integer, String, Text, Boolean, Enum, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from database.db import Base
import enum
from datetime import datetime

# class PostStatus(str, enum.Enum):
#     approved = "approved"
#     scheduled = "scheduled"
#     posted = "posted"
#     disapproved = "disapproved"

class ThemeStatus(str, enum.Enum):
    pending = "pending"
    selected = "selected"
    discarded = "discarded"

class CampaignStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    archived = "archived"

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    repeat_every_days = Column(Integer, nullable=False)
    target_customer = Column(String)
    insight = Column(String)
    description = Column(Text)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.draft)
    start_date = Column(Date, nullable=True)
    last_run_date = Column(Date, nullable=True)
    next_run_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)

    current_step = Column(Integer, nullable=False, server_default="0")
    

    themes = relationship("Theme", back_populates="campaign")
    posts = relationship("ContentPost", back_populates="campaign")

class Theme(Base):
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    title = Column(String, nullable=False)
    story = Column(Text)
    is_selected = Column(Boolean, default=False)
    status = Column(Enum(ThemeStatus), default=ThemeStatus.pending)
    created_at = Column(DateTime, default=datetime.now)

    campaign = relationship("Campaign", back_populates="themes")
    posts = relationship("ContentPost", back_populates="theme")

class ContentPost(Base):
    __tablename__ = "content_posts"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    theme_id = Column(Integer, ForeignKey("themes.id"), nullable=False)
    title = Column(String)
    content = Column(Text)
    # status = Column(Enum(PostStatus, name="post_status", create_constraint=False, native_enum=False), default=PostStatus.approved)
    status = Column(String, default="approved")

    created_at = Column(DateTime, default=datetime.now)
    scheduled_date = Column(Date, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    feedback = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    video_url = Column(String, nullable=True)

    campaign = relationship("Campaign", back_populates="posts")
    theme = relationship("Theme", back_populates="posts")
