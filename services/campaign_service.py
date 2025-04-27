# from sqlalchemy.orm import Session
# from database.models import Campaign, Theme, ContentPost
# from typing import List, Tuple
# from services.content_generator import generate_theme_title_and_story, generate_posts_from_theme
from fastapi import UploadFile, HTTPException
from markitdown import MarkItDown
from io import BytesIO

async def process_file_content(file: UploadFile) -> str:
    """Extract text content from uploaded files (PDF, DOCX, TXT) using MarkItDown."""
    # Validate file type
    # Define allowed MIME types
    allowed_types = [
        "application/msword",  # .doc
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        "application/pdf",  # .pdf
        "text/plain",  # .txt
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Unsupported file type")


    # Read file content
    contents = await file.read()

    # Limit file size to 10MB
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 10 MB
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    # Convert to Markdown using MarkItDown
    try:
        md = MarkItDown(enable_plugins=False)
        result = md.convert(BytesIO(contents))
        return result.text_content
    except Exception as e:
        raise HTTPException(status_code=500, detail="fConversion failed {e}")

# async def create_campaign_from_file(
#     file: UploadFile,
#     campaign_title: str,
#     target_customer: str,
#     description: str,
#     repeat_every_days: int,
#     db: Session
# ) -> Campaign:
#     """Create a campaign and generate themes from file content"""
#     # Extract content from file
#     insight = await process_file_content(file)
    
#     # Create campaign
#     campaign = Campaign(
#         title=campaign_title,
#         target_customer=target_customer,
#         description=description,
#         repeat_every_days=repeat_every_days,
#         current_step=1
#     )
#     db.add(campaign)
#     db.commit()
#     db.refresh(campaign)
    
#     # Generate themes
#     themes_data = generate_theme_title_and_story(
#         campaign_title=campaign_title,
#         insight=insight,
#         description=description,
#         target_customer=target_customer
#     )
    
#     # Create themes
#     for title, story in themes_data:
#         theme = Theme(
#             campaign_id=campaign.id,
#             title=title,
#             story=story
#         )
#         db.add(theme)
    
#     db.commit()
#     return campaign

# async def generate_campaign_content(campaign_id: int, db: Session) -> List[ContentPost]:
#     """Generate content posts for all themes in a campaign"""
#     campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
#     if not campaign:
#         raise HTTPException(status_code=404, detail="Campaign not found")
    
#     themes = db.query(Theme).filter(Theme.campaign_id == campaign_id).all()
#     all_posts = []
    
#     for theme in themes:
#         posts = await generate_posts_from_theme(theme, db)
#         all_posts.extend(posts)
    
#     return all_posts