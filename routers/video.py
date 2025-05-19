from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.db import get_db, SessionLocal

from database.models import ContentPost
# from schemas import CampaignCreate, CampaignResponse, CampaignData

import os
import json
import time
import logging
import asyncio

from fastapi import BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from google import genai
from google.genai import types
from google.genai.types import Part
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

router = APIRouter(prefix="/api/v1/videos", tags=["Video"])

class VideoPrompt(BaseModel):
    title: str
    content: str
    visual_description: Optional[str] = None
    style_guide: Optional[str] = None

class VideoGenRequest(BaseModel):
    post_id: int
    content: str
    image_urls: list[str]

class VideoGenResponse(BaseModel):
    success: bool
    post_id: int

async def generate_video_prompt(content: str) -> VideoPrompt:
    """Generate an optimized video prompt using Gemini API."""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    system_prompt = """
    You are a video content expert. Your task is to transform text content into a visually descriptive prompt 
    that will be used to generate engaging video content. Focus on:
    1. Visual elements and scenes that capture the essence of the message
    2. Emotional tone and atmosphere
    3. Key moments and transitions
    4. Style and aesthetic direction
    
    Rewrite the following user video idea for Google Veo video generation, allowing only neutral mentions of 'person', 'people', 'figure', 'individual', 'crowd', or 'silhouette'.
    Do NOT use words like 'man', 'woman', 'boy', 'girl', 'child', 'family', 'father', 'mother', 'emotion', 'dream', 'inspire', 'hope', 'love', 'community', 'success', 'achievement', 'relationship', or anything about feelings.
    Do NOT describe facial expressions, smiles, hugs, or social interactions.
    Focus on the environment and actions, and add people only as a neutral presence.
    Examples:
    - A person walking along a forest path with sunlight streaming through the trees.
    - Several people riding bicycles on a country road under a blue sky.
    - Figures sitting quietly on park benches, surrounded by green trees.

    Avoid any direct product mentions or advertising language. Instead, focus on storytelling and emotional connection.
    """
    
    try:
        response = await client.aio.models.generate_content(
            model='gemini-2.0-flash',
            contents=content,
            config={
                'response_mime_type': 'application/json',
                'response_schema': VideoPrompt,
                'system_instruction': types.Part.from_text(text=system_prompt),
                'temperature': 0.7
            }
        )
        
        prompt_data = json.loads(response.text)
        return VideoPrompt(**prompt_data)
        
    except Exception as e:
        logging.error(f"Error generating video prompt: {str(e)}")
        # Return a basic prompt if generation fails
        return VideoPrompt(
            title="Video Content",
            content=content,
            visual_description="Create a visually engaging video that captures the essence of the message."
        )

def update_post_status(post_id: int, status: str, video_url: str=None, video_error=None, db: Session = None):
    # Sync version, you can adapt to async as needed
    # with SessionLocal() as db:
    #     stmt = (
    #         update(content_posts)
    #         .where(content_posts.c.id == post_id)
    #         .values(
    #             video_status=status,
    #             video_url=video_url,
    #             video_error=video_error
    #         )
    #     )
    #     db.execute(stmt)
    #     db.commit()

    post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
    if not post:
        return
    post.video_status = status
    if video_url is not None:
        post.video_url = video_url
    if video_error is not None:
        post.video_error = video_error
    db.commit()

def get_post_status(post_id: int, db: Session = None):
    # Raw sql
    # with SessionLocal() as db:
    #     stmt = select(
    #         content_posts.c.video_status,
    #         content_posts.c.video_url,
    #         content_posts.c.video_error
    #     ).where(content_posts.c.id == post_id)
    #     result = db.execute(stmt).fetchone()
    #     if result:
    #         return dict(result)
    #     return None

    post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
    if not post:
        return None
    return {
        "video_status": post.video_status,
        "video_url": post.video_url,
        "video_error": post.video_error,
    }

async def generate_video_url(post_id: int, content: str, image_urls: list[str]) -> str:
    # This function handles the actual video generation and returns the URL
    try:
        logging.info(f"Starting video generation for post {post_id}")
        PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "thematic-land-451915-j3")
        LOCATION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
        output_gcs = "gs://bucket_nextcopy/video/"
        logging.info(f"Using GCS output path: {output_gcs}")

        # Generate optimized video prompt
        video_prompt = await generate_video_prompt(content)
        logging.info(f"Generated video prompt: {video_prompt.title}")

        # Initialize the Vertex AI client
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

        # Configure video generation with enhanced prompt
        operation = client.models.generate_videos(
            model="veo-2.0-generate-001",  # Use appropriate model name
            prompt=f"{video_prompt.visual_description}\n\nStyle: {video_prompt.style_guide if video_prompt.style_guide else 'Natural and authentic'}",
            config=types.GenerateVideosConfig(
                aspect_ratio="9:16",
                output_gcs_uri=output_gcs,
                number_of_videos=1,
                duration_seconds=8,
                person_generation="allow_adult",
                enhance_prompt=True,
            ),
        )

        # Wait for the operation to complete
        while not operation.done:
            await asyncio.sleep(15)
            operation = client.operations.get(operation)
            logging.info("Waiting for video generation to complete...")

        if not operation.response:
            raise Exception("Video generation failed")

        # Get the video URI and convert to public URL
        logging.info("Video generation completed, retrieving video URI")
        video_uri = operation.result.generated_videos[0].video.uri
        logging.info(f"Generated video URI: {video_uri}")
        if not video_uri.startswith("gs://"):
            raise Exception("Invalid GCS URI format")

        # Extract bucket and blob names
        path_parts = video_uri[5:].split("/", 1)
        bucket_name = path_parts[0]
        blob_name = path_parts[1] if len(path_parts) > 1 else ""

        if not blob_name:
            raise Exception("Invalid blob path in GCS URI")

        # Get public URL
        from google.cloud import storage
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        public_url = blob.public_url
        logging.info(f"Generated public URL: {public_url}")

        if not public_url:
            raise Exception("Failed to generate public URL")

        return public_url
    except Exception as e:
        logging.error(f"Error generating video: {str(e)}")
        raise

async def video_generation_task(post_id: int, content: str, image_urls: list[str]):
    # Create a new session for this background task
    with SessionLocal() as db:
        update_post_status(post_id, "processing", db=db)
        try:
            # Call the separate video generation function
            video_url = await generate_video_url(post_id, content, image_urls)
            update_post_status(post_id, "completed", video_url=video_url, db=db)
        except Exception as e:
            update_post_status(post_id, "failed", video_error=str(e), db=db)

@router.post("/generate", response_model=VideoGenResponse)
async def generate_video(req: VideoGenRequest, db: Session = Depends(get_db)):
    # Mark as pending right away
    print(req.content)
    update_post_status(req.post_id, "pending", db=db)
    # Start async background task
    asyncio.create_task(
        video_generation_task(req.post_id, req.content, req.image_urls)
    )
    return VideoGenResponse(success=True, post_id=req.post_id)

@router.get("/status/{post_id}")
async def get_status(post_id: int, db: Session = Depends(get_db)):
    info = get_post_status(post_id, db=db)
    if not info:
        raise HTTPException(status_code=404, detail="Post not found")
    return {
        "status": info["video_status"],
        "video_url": info["video_url"],
        "error": info["video_error"]
    }