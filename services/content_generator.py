import random
from sqlalchemy.orm import Session
from database.models import ContentPost, PostStatus, Campaign, Theme
from datetime import datetime, timedelta

def generate_theme_title_and_story(campaign_title: str, insight: str) -> tuple[str, str]:
    title_templates = [
        "The Power of {keyword}",
        "Mastering {keyword} for Growth",
        "Why {keyword} Matters Now",
        "{keyword}: A New Approach",
        "Unlocking {keyword}"
    ]

    insight_keywords = insight.split()
    keyword = random.choice(insight_keywords if insight_keywords else ["change"])
    title = random.choice(title_templates).format(keyword=keyword.capitalize())

    story = f"This theme explores how '{keyword}' relates to {campaign_title.lower()}. We’ll break down why this is crucial and how to apply it practically."
    return title, story

def generate_posts_from_theme(theme: Theme, db: Session) -> int:
    campaign = db.query(Campaign).filter(Campaign.id == theme.campaign_id).first()
    if not campaign:
        return 0

    # Ensure theme context is up-to-date
    theme = db.query(Theme).filter(Theme.id == theme.id).first()
    if not theme:
        return 0

    num_posts = campaign.repeat_every_days + 5
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