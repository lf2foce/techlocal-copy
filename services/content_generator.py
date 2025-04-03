import random
from sqlalchemy.orm import Session
from database.models import ContentPost, PostStatus, Campaign, Theme
from datetime import datetime, timedelta
from typing import Dict, Any
from pydantic import BaseModel, ValidationError
from google import genai
from google.genai import types
import json
import time
import os
from dotenv import load_dotenv
from typing import List, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
import asyncio

load_dotenv()

# def generate_theme_title_and_story(campaign_title: str, insight: str) -> tuple[str, str]:
#     title_templates = [
#         "The Power of {keyword}",
#         "Mastering {keyword} for Growth",
#         "Why {keyword} Matters Now",
#         "{keyword}: A New Approach",
#         "Unlocking {keyword}"
#     ]

#     insight_keywords = insight.split()
#     keyword = random.choice(insight_keywords if insight_keywords else ["change"])
#     title = random.choice(title_templates).format(keyword=keyword.capitalize())

#     story = f"This theme explores how '{keyword}' relates to {campaign_title.lower()}. We’ll break down why this is crucial and how to apply it practically."
#     return title, story

class Theme(BaseModel):
    title: str
    story: str
# worked
def generate_theme_title_and_story(campaign_title: str, insight: str, description: str, target_customer:str) -> tuple[str, str]:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # Generate response using Gemini API (synchronous version)
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=f"Please help me create theme for {campaign_title} {insight} {target_customer}",
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=Theme,
            system_instruction=types.Part.from_text(text=description),
        ),
    )
    
    # Extract the response
    print("Generated post based on user prompt.")
    content = json.loads(response.text)
    
    # Validate and parse the response using Pydantic
    blog_post = Theme(**content)
    
    return blog_post.title, blog_post.story

def generate_posts_from_theme(theme: Theme, db: Session) -> int:
    campaign = db.query(Campaign).filter(Campaign.id == theme.campaign_id).first()
    if not campaign:
        return 0

    # Ensure theme context is up-to-date
    theme = db.query(Theme).filter(Theme.id == theme.id).first()
    if not theme:
        return 0

    num_posts = campaign.repeat_every_days
    now = datetime.now()

    for i in range(num_posts):
        post = ContentPost(
            campaign_id=campaign.id,
            theme_id=theme.id,
            title=f"Post {i+1} - {theme.title}",
            content=f"This post is based on theme: '{theme.title}'\n\n{theme.story}\n\nGenerated item {i+1} in the campaign '{campaign.title}'.",
            status=PostStatus.scheduled,
            created_at=now + timedelta(microseconds=i)
        )
        db.add(post)

    db.commit()
    return num_posts

def approve_post(post_id: int, db: Session) -> ContentPost:
    post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
    if not post:
        raise ValueError("Post not found")

    post.status = PostStatus.scheduled
    db.commit()
    return post
