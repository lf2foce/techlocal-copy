from sqlalchemy import Column, Integer, String, Text, Boolean, Enum, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from database.db import Base
import enum
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB

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

    current_step = Column(Integer, nullable=False)
    campaign_data = Column(JSONB, nullable=True)  # Thay đổi từ Text sang JSONB
    content_type = Column(String, nullable=True)
    
    # 🔑 Thêm liên kết đến bảng users
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    # 🔄 Quan hệ ngược lại nếu bạn tạo User class
    user = relationship("User", back_populates="campaigns")
    themes = relationship("Theme", back_populates="campaign")
    posts = relationship("ContentPost", back_populates="campaign")

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)  # clerk_user_id
    name = Column(String)
    email = Column(String, unique=True, nullable=False)
    email_verified = Column(Boolean, default=False)
    image_url = Column(String)
    role = Column(String, default="user")
    preferences = Column(JSONB)
    credits_remaining = Column(Integer, default=100)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime)
    updated_at = Column(DateTime, default=datetime)

    # Quan hệ ngược lại
    campaigns = relationship("Campaign", back_populates="user")
    credit_logs = relationship("CreditLog", back_populates="user")
    
class Theme(Base):
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    title = Column(String, nullable=False)
    story = Column(Text)
    content_plan = Column(JSONB, nullable=True)
    is_selected = Column(Boolean, default=False)
    status = Column(Enum(ThemeStatus), default=ThemeStatus.pending)
    post_status = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    campaign = relationship("Campaign", back_populates="themes")
    posts = relationship("ContentPost", back_populates="theme")

class CreditLog(Base):
    __tablename__ = "credit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = Column(String, nullable=False)
    credits_used = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    credit_metadata = Column(JSONB)

    # Quan hệ với User
    user = relationship("User", back_populates="credit_logs")

class ContentPost(Base):
    __tablename__ = "content_posts"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    theme_id = Column(Integer, ForeignKey("themes.id"), nullable=False)
    title = Column(String)
    content = Column(Text)
    status = Column(String, default="approved")

    created_at = Column(DateTime, default=datetime.now)
    scheduled_date = Column(Date, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    feedback = Column(Text, nullable=True)
    image_status = Column(String, default="pending")
    image_url = Column(String, nullable=True)
    images = Column(JSONB)
    video_url = Column(String, nullable=True)
    post_metadata = Column(JSONB, nullable=True)

    campaign = relationship("Campaign", back_populates="posts")
    theme = relationship("Theme", back_populates="posts")
