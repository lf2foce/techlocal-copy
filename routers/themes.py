from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import time  # Add this import
from database.db import get_db
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

    themes_data = generate_theme_title_and_story(
        campaign.title, campaign.insight, campaign.description, campaign.target_customer
    )

    new_themes = []
    print('starting create theme')

    for theme_data in themes_data:
        title = theme_data["title"]
        story = theme_data["story"]
        content_plan = theme_data["content_plan"]

        theme = Theme(
            campaign_id=campaign_id,
            title=title,
            story=story,
            content_plan=content_plan,  # already dict format
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

async def generate_posts_background(theme_id: int, db: Session):
    from database.db import SessionLocal
    
    db = SessionLocal()
    try:
        theme = db.query(Theme).filter(Theme.id == theme_id).first()
        if not theme:
            await send_telegram_message(f"⚠️ Theme {theme_id} not found in background task")
            return
            
        # Fetch campaign data for more context
        campaign = db.query(Campaign).filter(Campaign.id == theme.campaign_id).first()
        if not campaign:
            await send_telegram_message(f"⚠️ Campaign not found for theme {theme_id}")
            return
            
        # Set post_status to pending before generation starts
        theme.post_status = "pending"
        db.commit()
        
        # Kiểm tra campaign_data trước khi sử dụng
        campaign_data = campaign.campaign_data if campaign.campaign_data else {}
        
        # Kiểm tra và xử lý content_plan nếu nó là None hoặc không có cấu trúc mong đợi
        print('1')
        content_plan = theme.content_plan or '{}'
        print('2', content_plan)
        print(type(content_plan))
        
        # Chuyển đổi chuỗi JSON thành từ điển
        if isinstance(content_plan, str):
            try:
                content_plan = json.loads(content_plan)
            except json.JSONDecodeError:
                await send_telegram_message(f"⚠️ Không thể phân tích chuỗi JSON của content_plan cho theme {theme_id}")
                return
        
        titles = content_plan.get('titles', [])
        print(titles)
        if not titles:
            await send_telegram_message(f"⚠️ Không tìm thấy tiêu đề trong content_plan cho theme {theme_id}")
            return
        print('3')
        # Now we can properly await the async function with complete campaign data
        generated_count = await generate_posts_from_theme(theme, db, campaign_data=campaign_data)
        
        # Update theme post_status to ready after successful generation
        theme.post_status = "ready"
        db.commit()
        
        await send_telegram_message(f"✨ Successfully generated {generated_count} posts from theme {theme.id}")
    except Exception as post_gen_error:
        if theme:
            theme.post_status = "error"
            db.commit()
        await send_telegram_message(f"⚠️ Warning: Posts were not generated due to an error: {str(post_gen_error)}")
    finally:
        db.close()

@router.post("/{theme_id}/select", response_model=ThemeResponse)
async def select_theme(theme_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    theme = db.query(Theme).filter(Theme.id == theme_id).first()
    if not theme:
        error_msg = f"Theme {theme_id} not found"
        # await send_telegram_message(f"❌ Failed to select theme: {error_msg}")
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
        # success_msg = f"✅ Theme selected (ID: {theme.id}): {theme.title}\n📝 Posts will be generated in background..."
        # await send_telegram_message(success_msg)

        # Schedule post generation as a background task
        background_tasks.add_task(generate_posts_background, theme.id, db)

        return theme
    except Exception as e:
        db.rollback()
        error_msg = f"An error occurred while processing theme {theme_id}: {str(e)}"
        await send_telegram_message(f"❌ Failed to select theme: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
