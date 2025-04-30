from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import time  # Add this import
from database.db import get_db, SessionLocal
from database.models import Campaign, Theme, ThemeStatus
from schemas import ThemeResponse
from typing import List
from services.content_generator import generate_theme_title_and_story, generate_posts_from_theme
from services.telegram_handler import send_telegram_message
import json

router = APIRouter(prefix="/themes", tags=["Themes"])

@router.post("/campaigns/{campaign_id}/generate_themes", response_model=List[ThemeResponse])
async def generate_themes(campaign_id: int, db: Session = Depends(get_db)):
    start_time = time.time()
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    db.query(Theme).filter(Theme.campaign_id == campaign_id).delete()

    # Get themes data concurrently
    themes_data = await generate_theme_title_and_story(
        campaign.title, campaign.insight, campaign.description, campaign.target_customer, campaign.repeat_every_days
    )

    new_themes = []
    print('starting create theme')

    # Process themes sequentially since we're working with DB
    for theme_data in themes_data:
        title = theme_data["title"]
        story = theme_data["story"]
        content_plan = theme_data["content_plan"]
        print(content_plan)
        theme = Theme(
            campaign_id=campaign_id,
            title=title,
            story=story,
            content_plan=content_plan,
            status=ThemeStatus.pending
        )
        db.add(theme)
        db.flush()
        new_themes.append(theme)

    campaign.current_step = 2
    db.commit()
    
    execution_time = time.time() - start_time
    print(f"⏱️ Theme generation completed in {execution_time:.2f} seconds")

    return new_themes


@router.get("/campaigns/{campaign_id}", response_model=List[ThemeResponse])
async def list_themes_by_campaign(campaign_id: int, db: Session = Depends(get_db)):
    return db.query(Theme).filter(Theme.campaign_id == campaign_id).order_by(Theme.id).all()

@router.get("/{theme_id}", response_model=ThemeResponse)
async def get_theme(theme_id: int, db: Session = Depends(get_db)):
    theme = db.query(Theme).filter(Theme.id == theme_id).first()
    if not theme:
        raise HTTPException(status_code=404, detail=f"Theme {theme_id} not found")
    return theme

@router.get("/{theme_id}/status", response_model=ThemeResponse)
async def check_theme_status(theme_id: int, db: Session = Depends(get_db)):
    theme = db.query(Theme).filter(Theme.id == theme_id).first()
    if not theme:
        raise HTTPException(status_code=404, detail=f"Theme {theme_id} not found")
    
    # await send_telegram_message(f"🔍 Status check for theme {theme_id}: {theme.post_status}")
    return theme

# Update the background task to use a factory for DB sessions
async def generate_posts_background(theme_id: int, db_factory):
    """Background task to generate posts with proper DB session management"""
    # Create a fresh DB session
    with db_factory() as db:
        theme = db.query(Theme).filter(Theme.id == theme_id).first()
        if not theme:
            await send_telegram_message(f"⚠️ Theme {theme_id} not found")
            return
            
        print(f"DEBUG: Starting post generation for theme {theme_id}")
        
        # Set status to pending
        theme.post_status = "pending"
        db.commit()
        
        # Fetch campaign data
        campaign = db.query(Campaign).filter(Campaign.id == theme.campaign_id).first()
        if not campaign:
            await send_telegram_message(f"⚠️ Campaign not found for theme {theme_id}")
            return
            
        campaign_data = campaign.campaign_data if campaign.campaign_data else {}
    
    try:
        # Call generate_posts_from_theme with the db_factory
        generated_count = await generate_posts_from_theme(theme, db_factory, campaign_data=campaign_data)
        
        # Update theme status with a fresh session
        with db_factory() as db:
            theme = db.query(Theme).filter(Theme.id == theme_id).first()
            if theme:
                theme.post_status = "ready"
                db.commit()
        
        await send_telegram_message(f"✨ Successfully generated {generated_count} posts for theme {theme_id}")
    except Exception as e:
        print(f"DEBUG: Error generating posts: {str(e)}")
        # Update status to error with a fresh session
        with db_factory() as db:
            theme = db.query(Theme).filter(Theme.id == theme_id).first()
            if theme:
                theme.post_status = "error"
                db.commit()
        
        await send_telegram_message(f"⚠️ Posts generation failed: {str(e)}")


# @router.post("/{theme_id}/select", response_model=ThemeResponse)
# async def select_theme(theme_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
#     theme = db.query(Theme).filter(Theme.id == theme_id).first()
#     if not theme:
#         error_msg = f"Theme {theme_id} not found"
#         # await send_telegram_message(f"❌ Failed to select theme: {error_msg}")
#         raise HTTPException(status_code=404, detail=error_msg)

#     # # Check if the theme is already in a final state
#     # if theme.status not in [ThemeStatus.pending]:
#     #     error_msg = f"Theme {theme_id} is already finalized as {theme.status.value}. You cannot select it again."
#     #     await send_telegram_message(f"❌ Failed to select theme: {error_msg}")
#     #     raise HTTPException(status_code=400, detail=error_msg)

#     # # Check if any theme in this campaign is already selected
#     # existing_selected = db.query(Theme).filter(
#     #     Theme.campaign_id == theme.campaign_id,
#     #     Theme.is_selected
#     # ).first()
#     # if existing_selected:
#     #     error_msg = f"Campaign already has theme {existing_selected.id} selected. Only one theme can be selected per campaign."
#     #     await send_telegram_message(f"❌ Failed to select theme: {error_msg}")
#     #     raise HTTPException(status_code=400, detail=error_msg)

#     try:
#         # Deselect all other themes in the same campaign
#         db.query(Theme).filter(
#             Theme.campaign_id == theme.campaign_id,
#             Theme.id != theme.id
#         ).update({"is_selected": False, "status": ThemeStatus.discarded})

#         theme.is_selected = True
#         theme.status = ThemeStatus.selected
        
#         # Update campaign step to indicate theme selection is complete
#         campaign = db.query(Campaign).filter(Campaign.id == theme.campaign_id).first()
#         campaign.current_step = 3
#         db.commit()
        
#         # Send success message with theme details
#         # success_msg = f"✅ Theme selected (ID: {theme.id}): {theme.title}\n📝 Posts will be generated in background..."
#         # await send_telegram_message(success_msg)

#         # Schedule post generation as a background task
#         background_tasks.add_task(generate_posts_background, theme.id, db)

#         return theme
#     except Exception as e:
#         db.rollback()
#         error_msg = f"An error occurred while processing theme {theme_id}: {str(e)}"
#         await send_telegram_message(f"❌ Failed to select theme: {error_msg}")
#         raise HTTPException(status_code=500, detail=error_msg)

# Update the route to use a DB factory
@router.post("/{theme_id}/select", response_model=ThemeResponse)
async def select_theme(theme_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Create a db_factory that returns a fresh session each time
    def db_factory():
        return SessionLocal()
    
    theme = db.query(Theme).filter(Theme.id == theme_id).first()
    if not theme:
        raise HTTPException(status_code=404, detail=f"Theme {theme_id} not found")

    try:
        # Update theme and campaign status
        db.query(Theme).filter(
            Theme.campaign_id == theme.campaign_id,
            Theme.id != theme.id
        ).update({"is_selected": False, "status": ThemeStatus.discarded})

        theme.is_selected = True
        theme.status = ThemeStatus.selected
        
        campaign = db.query(Campaign).filter(Campaign.id == theme.campaign_id).first()
        campaign.current_step = 3
        db.commit()
        
        # Add the background task with the db_factory
        background_tasks.add_task(generate_posts_background, theme.id, db_factory)

        return theme
    except Exception as e:
        db.rollback()
        error_msg = f"An error occurred: {str(e)}"
        await send_telegram_message(f"❌ Failed to select theme: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)