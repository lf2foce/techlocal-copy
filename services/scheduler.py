from sqlalchemy.orm import Session
from database.models import ContentPost, Campaign, PostStatus
from datetime import date
from services.telegram_handler import send_telegram_message

def run_daily_schedule(db: Session) -> int:
    count = 0

    active_campaigns = db.query(Campaign).filter(Campaign.is_active).all()
    for campaign in active_campaigns:
        # Find the next scheduled post
        post = db.query(ContentPost).filter(
            ContentPost.campaign_id == campaign.id,
            ContentPost.status == PostStatus.scheduled
        ).order_by(ContentPost.created_at.asc(), ContentPost.id.asc()).first()

        if post:
            post.status = PostStatus.posted
            post.posted_at = date.today()
            db.commit()
            send_telegram_message(
                f"📢 Post from campaign '{campaign.title}' sent!\n\n{post.title}\n{post.content}"
            )
            count += 1

    return count
