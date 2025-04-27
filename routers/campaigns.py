from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import Campaign
from schemas import CampaignCreate, CampaignResponse
from typing import List


router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

@router.get("/", response_model=List[CampaignResponse])
def list_campaigns(db: Session = Depends(get_db)):
    return db.query(Campaign).order_by(Campaign.id.desc()).all()

@router.get("/top", response_model=List[CampaignResponse])
def get_top_campaigns(db: Session = Depends(get_db)):
    return db.query(Campaign).order_by(Campaign.last_run_date.desc()).limit(5).all()

@router.post("/", response_model=CampaignResponse)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    new_campaign = Campaign(**payload.model_dump())
    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)
    return new_campaign

@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    db.delete(campaign)
    db.commit()
    return None

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Extract text from uploaded file"""
    try:
        from services.campaign_service import process_file_content
        text = await process_file_content(file)
        return {
            "text": text,
            "filename": file.filename,
            "message": "Text extraction completed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))