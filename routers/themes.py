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
        title, story = generate_theme_title_and_story(campaign.title, campaign.insight)
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

    db.commit()
    return new_themes

@router.get("/campaigns/{campaign_id}", response_model=List[ThemeResponse])
async def list_themes_by_campaign(campaign_id: int, db: Session = Depends(get_db)):
    return db.query(Theme).filter(Theme.campaign_id == campaign_id).order_by(Theme.id).all()

@router.post("/{theme_id}/select", response_model=ThemeResponse)
async def select_theme(theme_id: int, db: Session = Depends(get_db)):
    theme = db.query(Theme).filter(Theme.id == theme_id).first()
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    # Deselect all other themes in the same campaign
    db.query(Theme).filter(
        Theme.campaign_id == theme.campaign_id,
        Theme.id != theme.id
    ).update({"is_selected": False, "status": ThemeStatus.discarded})

    theme.is_selected = True
    theme.status = ThemeStatus.selected
    db.commit()
    await send_telegram_message(f"✅ Theme selected (ID: {theme.id}): {theme.title}")

    # Automatically trigger post generation after selecting a theme
    generated_count = generate_posts_from_theme(theme, db)
    await send_telegram_message(f"📝 {generated_count} posts generated from theme {theme.id}")

    return theme
