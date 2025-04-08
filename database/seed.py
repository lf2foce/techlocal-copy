from database.db import SessionLocal, Base, engine
from database.models import Campaign, Theme, ContentPost, ThemeStatus, CampaignStatus
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
        
        # Create sample campaigns with realistic marketing scenarios
        campaign_data = [
            {
                "title": "Summer Fashion Collection Launch",
                "repeat_every_days": 3,
                "target_customer": "Fashion-conscious women aged 25-35",
                "insight": "Young professionals seeking trendy yet comfortable summer wear",
                "description": "Showcase our new summer collection with focus on sustainable materials and versatile styles",
                "status": CampaignStatus.active,
                "is_active": True
            },
            {
                "title": "Healthy Living Wellness Program",
                "repeat_every_days": 5,
                "target_customer": "Health-conscious individuals aged 30-50",
                "insight": "Growing interest in holistic wellness and preventive health care",
                "description": "Promote wellness products and share expert health tips",
                "status": CampaignStatus.active,
                "is_active": True
            },
            {
                "title": "Tech Gadget Holiday Special",
                "repeat_every_days": 2,
                "target_customer": "Tech enthusiasts and early adopters",
                "insight": "High demand for latest gadgets during holiday season",
                "description": "Holiday promotion for premium tech products with special bundles",
                "status": CampaignStatus.draft,
                "is_active": False
            }
        ]
        
        campaigns = []
        for data in campaign_data:
            campaign = Campaign(
                **data,
                start_date=datetime.now().date(),
                last_run_date=datetime.now().date() - timedelta(days=random.randint(1, 10)),
                next_run_date=datetime.now().date() + timedelta(days=random.randint(1, 7)),
                current_step=4
            )
            campaigns.append(campaign)
        
        db.add_all(campaigns)
        db.commit()
        
        # Create themed content strategies for each campaign
        theme_data = {
            "Summer Fashion Collection Launch": [
                ("Sustainable Fashion", "Highlighting eco-friendly materials and sustainable production practices"),
                ("Summer Office Style", "Professional looks that keep you cool in the summer heat"),
                ("Weekend Getaway Fashion", "Versatile pieces perfect for summer travel and leisure")
            ],
            "Healthy Living Wellness Program": [
                ("Mindful Living", "Daily practices for mental and emotional wellbeing"),
                ("Nutrition Essentials", "Balanced diet tips and healthy recipe ideas"),
                ("Active Lifestyle", "Incorporating movement into daily routines")
            ],
            "Tech Gadget Holiday Special": [
                ("Smart Home Innovation", "Transform your home with cutting-edge smart devices"),
                ("Productivity Tech", "Gadgets that boost work efficiency"),
                ("Entertainment Tech", "Latest gaming and entertainment devices")
            ]
        }
        
        for campaign in campaigns:
            themes = []
            for i, (title, story) in enumerate(theme_data[campaign.title]):
                theme = Theme(
                    campaign_id=campaign.id,
                    title=title,
                    story=story,
                    is_selected=i == 0,
                    status=ThemeStatus.selected if i == 0 else ThemeStatus.pending,
                    created_at=datetime.now() - timedelta(days=random.randint(1, 15))
                )
                themes.append(theme)
            
            db.add_all(themes)
            db.commit()
            
            # Create engaging posts for each theme
            for theme in themes:
                posts = [
                    ContentPost(
                        campaign_id=campaign.id,
                        theme_id=theme.id,
                        title=f"Exciting {theme.title} Update #{i+1}",
                        content=f"🌟 New {theme.title} Highlight! \n\n{theme.story} \n\n#Innovation #Trending #MustHave",
                        status='approved' if campaign.is_active else 'draft',
                        created_at=datetime.now() - timedelta(days=random.randint(1, 15)),
                        scheduled_date=datetime.now().date() + timedelta(days=i*campaign.repeat_every_days),
                        posted_at=datetime.now() - timedelta(days=random.randint(1, 15)) if campaign.is_active and i == 0 else None
                    ) for i in range(3)
                ]
                
                db.add_all(posts)
                db.commit()
        
        print("Database seeded successfully with realistic marketing content")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()