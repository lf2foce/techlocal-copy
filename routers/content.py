from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import ContentPost, Theme
from schemas import ContentPostResponse
from typing import List
from services.telegram_handler import send_telegram_message
from services.content_generator import approve_post as approve_post_logic
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
