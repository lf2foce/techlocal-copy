from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import Campaign, Theme, ThemeStatus
from schemas import ThemeResponse
from typing import List
from services.content_generator import generate_theme_title_and_story, generate_posts_from_theme
from services.telegram_handler import send_telegram_message

router = APIRouter(prefix="/themes", tags=["Themes"])

@router.post("/campaigns/{campaign_id}/generate_themes", response_model=List[ThemeResponse])
async def generate_themes(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Remove old themes for clean slate
    db.query(Theme).filter(Theme.campaign_id == campaign_id).delete()

    new_themes = []
    for _ in range(5):
        title, story = generate_theme_title_and_story(campaign.title, campaign.insight, campaign.description, campaign.target_customer)
        theme = Theme(
            campaign_id=campaign_id,
            title=title,
            story=story,
            status=ThemeStatus.pending
        )
        db.add(theme)
        db.flush()  # Get ID for telegram
        await send_telegram_message(f"🎯 New theme created (ID: {theme.id}): {title}\n{story}")
        new_themes.append(theme)

    # Update campaign step after successful theme generation
    campaign.current_step = 2
    db.commit()
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

@router.post("/{theme_id}/select", response_model=ThemeResponse)
async def select_theme(theme_id: int, db: Session = Depends(get_db)):
    theme = db.query(Theme).filter(Theme.id == theme_id).first()
    if not theme:
        error_msg = f"Theme {theme_id} not found"
        await send_telegram_message(f"❌ Failed to select theme: {error_msg}")
        raise HTTPException(status_code=404, detail=error_msg)

    # # Check if the theme is already in a final state
    # if theme.status not in [ThemeStatus.pending]:
    #     error_msg = f"Theme {theme_id} is already finalized as {theme.status.value}. You cannot select it again."
    #     await send_telegram_message(f"❌ Failed to select theme: {error_msg}")
    #     raise HTTPException(status_code=400, detail=error_msg)

    # # Check if any theme in this campaign is already selected
    # existing_selected = db.query(Theme).filter(
    #     Theme.campaign_id == theme.campaign_id,
    #     Theme.is_selected
    # ).first()
    # if existing_selected:
    #     error_msg = f"Campaign already has theme {existing_selected.id} selected. Only one theme can be selected per campaign."
    #     await send_telegram_message(f"❌ Failed to select theme: {error_msg}")
    #     raise HTTPException(status_code=400, detail=error_msg)

    try:
        # Deselect all other themes in the same campaign
        db.query(Theme).filter(
            Theme.campaign_id == theme.campaign_id,
            Theme.id != theme.id
        ).update({"is_selected": False, "status": ThemeStatus.discarded})

        theme.is_selected = True
        theme.status = ThemeStatus.selected
        
        # Update campaign step to indicate theme selection is complete
        campaign = db.query(Campaign).filter(Campaign.id == theme.campaign_id).first()
        campaign.current_step = 3
        db.commit()
        
        # Send success message with theme details
        success_msg = f"✅ Theme selected (ID: {theme.id}): {theme.title}\n📝 Generating posts..."
        await send_telegram_message(success_msg)

        # Automatically trigger post generation after selecting a theme
        try:
            generated_count = generate_posts_from_theme(theme, db)
            await send_telegram_message(f"✨ Successfully generated {generated_count} posts from theme {theme.id}")
        except Exception as post_gen_error:
            await send_telegram_message(f"⚠️ Warning: Posts were not generated due to an error: {str(post_gen_error)}")

        return theme
    except Exception as e:
        db.rollback()
        error_msg = f"An error occurred while processing theme {theme_id}: {str(e)}"
        await send_telegram_message(f"❌ Failed to select theme: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
