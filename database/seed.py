from database.db import SessionLocal, Base, engine
from database.models import Campaign, Theme, ContentPost, GenerationMode, ThemeStatus, CampaignStatus, PostStatus
from datetime import datetime, timedelta
import random

def seed_database():
    """Initialize database with sample data"""
    db = SessionLocal()
    
    try:
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)
        
        # Check if data already exists
        if db.query(Campaign).count() > 0:
            print("Database already seeded")
            return
        
        # Create sample campaigns
        campaigns = [
            Campaign(
                title=f"Campaign {i}",
                repeat_every_days=7,
                target_customer=f"Target Group {i}",
                insight=f"Customer insight {i}",
                description=f"Description for campaign {i}",
                generation_mode=random.choice(list(GenerationMode)),
                status=random.choice(list(CampaignStatus)),
                start_date=datetime.now().date(),
                last_run_date=datetime.now().date() - timedelta(days=random.randint(1, 30)),
                next_run_date=datetime.now().date() + timedelta(days=random.randint(1, 30)),
                is_active=random.choice([True, False])
            ) for i in range(1, 4)
        ]
        
        db.add_all(campaigns)
        db.commit()
        
        # Create sample themes for each campaign
        for campaign in campaigns:
            themes = [
                Theme(
                    campaign_id=campaign.id,
                    title=f"Theme {i} for {campaign.title}",
                    story=f"Story for theme {i} of campaign {campaign.id}",
                    is_selected=i == 1,
                    status=ThemeStatus.selected if i == 1 else random.choice(list(ThemeStatus)),
                    created_at=datetime.now() - timedelta(days=random.randint(1, 30))
                ) for i in range(1, 4)
            ]
            
            db.add_all(themes)
            db.commit()
            
            # Create sample posts for each theme
            for theme in themes:
                posts = [
                    ContentPost(
                        campaign_id=campaign.id,
                        theme_id=theme.id,
                        title=f"Post {i} for theme {theme.id}",
                        content=f"Content for post {i} of theme {theme.id}",
                        status=random.choice(list(PostStatus)),
                        created_at=datetime.now() - timedelta(days=random.randint(1, 30)),
                        scheduled_date=datetime.now().date() + timedelta(days=random.randint(1, 30)),
                        posted_at=datetime.now() - timedelta(days=random.randint(1, 30)) if random.choice([True, False]) else None
                    ) for i in range(1, 4)
                ]
                
                db.add_all(posts)
                db.commit()
        
        print("Database seeded successfully")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()