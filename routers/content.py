from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import ContentPost, Theme
from schemas import ContentPostResponse
from typing import List
from services.telegram_handler import send_telegram_message
from services.content_generator import approve_post as approve_post_logic
from services.image_prompt_generator import generate_image_prompts
from services.gemini_image_handler import generate_and_upload_async
from services.ideogram_handler import generate_and_upload_ideogram
from fastapi import BackgroundTasks


import asyncio
import requests
import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter(prefix="/content", tags=["Content"])

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

@router.post("/{post_id}/generate_images_real")
async def generate_real_images_for_post(post_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Update post status to indicate image generation is in progress
    post.image_status = "generating"
    db.commit()

    async def generate_images_background():
        try:
            # Create a new session for database updates
            from database.db import SessionLocal
            async_db = SessionLocal()
            try:
                # Get fresh post instance in this session
                post_instance = async_db.query(ContentPost).filter(ContentPost.id == post_id).first()
                if not post_instance:
                    raise ValueError(f"Post {post_id} not found")

                # Generate prompts in background
                prompt_tuples = generate_image_prompts(post_instance.content)
                # Extract only english_prompts for image generation
                prompts = [eng for _, eng, _ in prompt_tuples]

                print('prompts: ', prompts)
                print("start generating images")

                # Generate images using Ideogram
                urls = await asyncio.gather(*[
                    generate_and_upload_ideogram(
                        prompt,
                        aspect_ratio="ASPECT_9_16"
                    ) 
                    for prompt in prompts
                ])

                # Build final image JSON
                images = []
                for i, (prompt, url) in enumerate(zip(prompts, urls)):
                    if url:  # Only add successful generations
                        images.append({
                            "url": url,
                            "prompt": prompt,
                            "order": i,
                            "isSelected": True,
                            "metadata": {
                                "width": 9,
                                "height": 16,
                                "style": "illustration"
                            }
                        })

                # Update post with generated images
                post_instance.images = {"images": images}
                post_instance.image_status = "completed" if images else "failed"
                async_db.commit()
            finally:
                async_db.close()

        except Exception as e:
            print(f"Error in background task: {str(e)}")
            # Create a new session for error handling
            async_db = SessionLocal()
            try:
                post_instance = async_db.query(ContentPost).filter(ContentPost.id == post_id).first()
                if post_instance:
                    post_instance.image_status = "failed"
                    async_db.commit()
            finally:
                async_db.close()

    # Schedule the background task
    background_tasks.add_task(generate_images_background)

    return {"status": "processing", "message": "Image generation started in background"}


# You can customize this list or plug in actual image generation logic
# MOCK_IMAGE_URLS = [
#     "https://images.unsplash.com/photo-1527090526205-beaac8dc3c62?q=80&w=600&auto=format&fit=crop",
#     "https://images.unsplash.com/photo-1445307806294-bff7f67ff225?q=80&w=600&auto=format&fit=crop",
#     "https://images.unsplash.com/photo-1519692933481-e162a57d6721?q=80&w=600&auto=format&fit=crop",
#     "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=600&auto=format&fit=crop"
# ]

# MOCK_STYLES = ["sketch", "artistic", "abstract", "cinematic", "illustration"]

# import random
# def mock_generate_images_for_post(post_id: int, db: Session):
#     post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
#     if not post:
#         raise HTTPException(status_code=404, detail="Post not found")

#     # Step 1: Get prompts from post content
#     prompt_tuples = generate_image_prompts(post.content)

#     # Step 2: Build the images field
#     images = []
#     for i, (part, english_prompt, vietnamese_explanation) in enumerate(prompt_tuples):
#         images.append({
#             "url": MOCK_IMAGE_URLS[i % len(MOCK_IMAGE_URLS)],
#             "prompt": english_prompt,
#             "order": i,
#             "isSelected": i in [2, 3],  # select last 2 by default
#             "metadata": {
#                 "width": 1024,
#                 "height": 1024,
#                 "style": random.choice(MOCK_STYLES)
#             }
#         })

#     # Step 3: Save to post
#     post.images = {"images": images}
#     db.commit()
#     db.refresh(post)

#     return post.images