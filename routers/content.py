from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import ContentPost, Theme, Campaign
from schemas import ContentPostResponse
from typing import List, Dict
from services.telegram_handler import send_telegram_message
from services.content_generator import approve_post as approve_post_logic
from services.image_prompt_generator import generate_image_prompts
from services.gemini_image_handler import generate_and_upload_async
from services.ideogram_handler import generate_and_upload_ideogram
from services.image_service_switcher import generate_image

from fastapi import BackgroundTasks
import pandas as pd
from io import BytesIO


import asyncio
import requests
import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter(prefix="/content", tags=["Content"])

@router.get("/export")
def export_posts(format: str = "excel", db: Session = Depends(get_db)):
    from services.data_export_service import export_to_excel
    
    if format.lower() == "excel":
        buffer, filename = export_to_excel(db)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        raise HTTPException(status_code=400, detail="Only Excel export is supported")
    
    return Response(
        content=buffer.getvalue(),
        media_type=media_type,
        headers={
            'Content-Disposition': f'attachment; filename={filename}'
        }
    )

@router.get("/posts/{post_id}", response_model=ContentPostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@router.get("/campaigns/{campaign_id}/posts", response_model=List[ContentPostResponse])
def list_campaign_posts(campaign_id: int, db: Session = Depends(get_db)):
    return db.query(ContentPost).filter(ContentPost.campaign_id == campaign_id).order_by(ContentPost.created_at).all()

@router.post("/{post_id}/disapprove", response_model=ContentPostResponse)
def disapprove_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.status = "disapproved"
    db.commit()
    send_telegram_message(f"❌ Post {post.id} has been disapproved.")
    return post

@router.post("/{post_id}/redo", response_model=ContentPostResponse)
def redo_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    theme = db.query(Theme).filter(Theme.id == post.theme_id).first()
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    post.content = f"[REGENERATED] Content based on theme '{theme.title}': {theme.story}"
    post.status = "scheduled"
    db.commit()
    send_telegram_message(f"🔁 Post {post.id} has been regenerated and rescheduled.")
    return post

@router.post("/{post_id}/approve", response_model=ContentPostResponse)
def approve_post(post_id: int, db: Session = Depends(get_db)):
    try:
        post = approve_post_logic(post_id, db)
        return post
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{post_id}/post_to_facebook", response_model=ContentPostResponse)
def post_to_facebook(post_id: int, db: Session = Depends(get_db)):
    post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    from services.facebook_handler import post_to_facebook
    success = post_to_facebook(post.content)
    if success:
        post.status = "posted"
        db.commit()
        return post
    else:
        raise HTTPException(status_code=400, detail="Failed to post to Facebook")

@router.get("/{post_id}/image_prompts")
def get_image_prompts(post_id: int, db: Session = Depends(get_db)):
    post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    prompts = generate_image_prompts(post.content)
    return {"prompts": [
        {"part": part, "english_prompt": eng, "vietnamese_explanation": vn}
        for part, eng, vn in prompts
    ]}

# @router.post("/{post_id}/generate_images")
# def generate_images_for_post(post_id: int, db: Session = Depends(get_db)):
#     result = mock_generate_images_for_post(post_id, db)
#     return {"status": "success", "images": result}

# Set up logger
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@router.post("/{post_id}/generate_images_real")
async def generate_real_images_for_post(
    post_id: int, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db), 
    num_images: int = None, 
    style: str = None, 
    image_service: str = "gemini"
):
    # Get values from query parameters or use defaults
    num_images = num_images if num_images is not None else 1
    style = style if style is not None else "realistic"
    logger.info(f"Received request with style: {style}, num_images: {num_images}, service: {image_service}")
    
    post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Update post status to indicate image generation is in progress
    post.image_status = "generating"
    post.image_progress = 0  # Assuming you've added this field to your model
    post.image_status_detail = "Queued for processing"
    db.commit()
    db.refresh(post)

    # Create a task that will run in the background
    asyncio.create_task(process_image_generation(post_id, num_images, style, image_service))
    
    return {
        "status": "processing", 
        "message": "Image generation started in background",
        "post_id": post_id
    }

# This function runs as a separate task in the event loop
async def process_image_generation(post_id: int, num_images: int, style: str, image_service: str):
    # Create a new session for database updates
    from database.db import SessionLocal
    async_db = None
    
    try:
        async_db = SessionLocal()
        
        # Get fresh post instance in this session
        post_instance = async_db.query(ContentPost).filter(ContentPost.id == post_id).first()
        if not post_instance:
            logger.error(f"Post {post_id} not found in background task")
            return

        try:
            # Update progress
            await update_progress(async_db, post_instance, 10, "Generating prompts")
            
            # Directly await the async function - no run_in_executor needed
            prompt_tuples = await generate_image_prompts(
                post_instance.content, 
                style=style, 
                num_prompts=num_images
            )
            
            # Extract only english_prompts for image generation
            prompts = [eng for _, eng, _ in prompt_tuples]
            
            logger.info(f"Generated {len(prompts)} prompts with style '{style}'")
            
            await update_progress(async_db, post_instance, 20, f"Starting generation of {len(prompts)} images")
            
            # Process images in parallel with semaphore to limit concurrency
            semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent image generations
            
            async def process_single_image(idx, prompt):
                async with semaphore:
                    try:
                        # Generate image
                        url = await generate_image(
                            prompt,
                            service=image_service,
                            post_id=post_id if image_service.lower() == "gemini" else None
                        )
                        
                        if url:
                            return {
                                "url": url,
                                "prompt": prompt,
                                "order": idx + 1,
                                "isSelected": True,
                                "provider": image_service,
                                "metadata": {
                                    "width": 9,
                                    "height": 16,
                                    "style": style
                                }
                            }
                        return None
                    except Exception as e:
                        logger.error(f"Error generating image {idx+1}: {str(e)}")
                        await update_progress(
                            async_db, 
                            post_instance, 
                            None,  # Don't update progress percentage
                            f"Error with image {idx+1}: {str(e)[:100]}"
                        )
                        return None
            
            # Create tasks for all images
            image_tasks = []
            for i, prompt in enumerate(prompts):
                task = process_single_image(i, prompt)
                image_tasks.append(task)
            
            # Process images and maintain original order
            results = await asyncio.gather(*image_tasks)
            
            # Filter out None results (failed generations) but preserve ordering
            images = [img for img in results if img]
            
            # Update progress
            await update_progress(
                async_db,
                post_instance,
                90,
                f"Generated {len(images)}/{len(prompts)} images successfully"
            )
            
            # Update post with generated images
            post_instance.images = {"images": images}
            post_instance.image_status = "completed" if images else "failed"
            post_instance.image_progress = 100
            post_instance.image_status_detail = f"Completed with {len(images)} images" if images else "Failed to generate any images"
            async_db.commit()
            
            logger.info(f"Successfully completed image generation for post {post_id}")
            
        except Exception as e:
            logger.exception(f"Error in image generation task: {str(e)}")
            post_instance.image_status = "failed"
            post_instance.image_status_detail = f"Error: {str(e)[:200]}"
            post_instance.image_progress = 0
            async_db.commit()
            
    finally:
        if async_db:
            async_db.close()

# Helper function to update progress
async def update_progress(db, post, progress=None, status_detail=None):
    try:
        if progress is not None:
            post.image_progress = progress
        if status_detail is not None:
            post.image_status_detail = status_detail
        db.commit()
        logger.debug(f"Updated progress for post {post.id}: {progress}%, {status_detail}")
    except Exception as e:
        logger.error(f"Failed to update progress: {str(e)}")


@router.post("/posts/batch_generate_images")
async def batch_generate_images(post_ids: List[int], background_tasks: BackgroundTasks, db: Session = Depends(get_db), num_images: int = None, style: str = None, image_service: str = "gemini"):
# Get values from query parameters or use defaults
    num_images = num_images if num_images is not None else 1
    style = style if style is not None else "realistic"
    
    # Validate all posts exist and update their status
    posts = db.query(ContentPost).filter(ContentPost.id.in_(post_ids)).all()
    found_ids = {post.id for post in posts}
    missing_ids = set(post_ids) - found_ids
    if missing_ids:
        raise HTTPException(status_code=404, detail=f"Posts not found: {missing_ids}")
    
    # Update status for all posts
    for post in posts:
        post.image_status = "generating"
    db.commit()
    [db.refresh(post) for post in posts]
    
    async def batch_generate_images_background():
        from database.db import SessionLocal
        async_db = SessionLocal()
        try:
            results = {}
            for post_id in post_ids:
                try:
                    post = async_db.query(ContentPost).filter(ContentPost.id == post_id).first()
                    prompt_tuples = generate_image_prompts(post.content, style=style, num_prompts=num_images)
                    prompts = [eng for _, eng, _ in prompt_tuples]
                    
                    urls = await asyncio.gather(*[
                        generate_image(
                            prompt,
                            service=image_service,
                            post_id=post_id if image_service.lower() == "gemini" else None
                        )
                        for prompt in prompts
                    ])
                    
                    images = []
                    for i, (prompt, url) in enumerate(zip(prompts, urls)):
                        if url:
                            images.append({
                                "url": url,
                                "prompt": prompt,
                                "order": i+1,
                                "isSelected": True,
                                "provider": image_service,
                                "metadata": {
                                    "width": 9,
                                    "height": 16,
                                    "style": style
                                }
                            })
                    
                    post.images = {"images": images}
                    post.image_status = "completed" if images else "failed"
                    results[post_id] = "success"
                except Exception as e:
                    post.image_status = "failed"
                    results[post_id] = str(e)
                    print(f"Error processing post {post_id}: {e}")
                finally:
                    async_db.commit()
                    async_db.refresh(post)
        finally:
            async_db.close()
    
    background_tasks.add_task(batch_generate_images_background)
    
    return {
        "status": "processing",
        "message": f"Batch image generation started for {len(post_ids)} posts",
        "post_ids": post_ids
    }
