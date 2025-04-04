from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, Campaign, Theme, ContentPost, ThemeStatus, PostStatus
from services.content_generator import save_posts_to_db
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Setup test database connection
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Create test data
test_posts = []
for i in range(20):
    test_posts.append({
        "title": f"Test Post {i+1}",
        "content": f"This is test content for post {i+1}"
    })

# Get a valid campaign and theme ID from the database
campaign = db.query(Campaign).first()
theme = db.query(Theme).filter(Theme.campaign_id == campaign.id).first()

if campaign and theme:
    print(f"Testing with Campaign ID: {campaign.id}, Theme ID: {theme.id}")
    print(f"Attempting to save {len(test_posts)} posts to database...")
    
    # Test the improved save_posts_to_db function
    saved_count = save_posts_to_db(test_posts, campaign.id, theme.id, db)
    
    # Verify the results
    print(f"Saved {saved_count} posts to database")
    
    # Count actual posts in database
    actual_count = db.query(ContentPost).filter(
        ContentPost.campaign_id == campaign.id,
        ContentPost.theme_id == theme.id
    ).count()
    
    print(f"Actual post count in database: {actual_count}")
else:
    print("No campaign or theme found in database for testing")

# Close the session
db.close()