from sqlalchemy.orm import Session
from database.models import ContentPost, Campaign
from datetime import date
from services.telegram_handler import send_telegram_message
from fastapi import HTTPException
import requests
import os
from dotenv import load_dotenv
load_dotenv()

def run_daily_schedule(db: Session) -> int:
    count = 0

    active_campaigns = db.query(Campaign).filter(Campaign.is_active).all()
    for campaign in active_campaigns:
        # Find the next scheduled post
        post = db.query(ContentPost).filter(
            ContentPost.campaign_id == campaign.id,
            ContentPost.status == "scheduled"
        ).order_by(ContentPost.created_at.asc(), ContentPost.id.asc()).first()

        if post:
            # Post to Facebook
            from services.facebook_handler import post_to_facebook
            success = post_to_facebook(post.content, campaign.title)
            if success:
                post.status = "posted"
                post.posted_at = date.today()
                db.commit()
                count += 1

    return count
