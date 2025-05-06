from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import Campaign
from schemas import CampaignCreate, CampaignResponse, CampaignData
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


from pydantic import BaseModel
from typing import Optional
import logging


import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.types import Part
from fastapi import BackgroundTasks
from typing import List, Optional
import time

load_dotenv()

class CampaignInput(BaseModel):
    id: int  # Add ID field as optional
    title: str
    description: str
    targetCustomer: str
    insight: str

class CampaignRequest(BaseModel):
    campaignInput: CampaignInput



class DescriptionPrompt(BaseModel):
    # Phong cách và mục tiêu nội dung
    toneWriting: str                      # Ví dụ: ấm áp, chuyên nghiệp, hài hước
    topicStyle: str                       # storytelling, quote, case study
    platforms: List[str]                  # ["Facebook", "TikTok"]
    imageMood: Optional[str]              # Ví dụ: thư giãn, năng lượng, ấm áp
    mindset: str                          # học hỏi, giải trí, truyền cảm hứng
    contentObjective: str                 # Mục tiêu chiến dịch: bán hàng, nhận diện, kích hoạt

    # Khách hàng mục tiêu
    targetCustomer: str                   # mô tả người mua lý tưởng (nhân khẩu học + hành vi)
    painPoints: List[str]                # các rào cản / lo lắng thường gặp
    bigKeywords: List[str]               # từ khóa sản phẩm / insight tìm kiếm

    # Định vị thương hiệu
    brandName: Optional[str]             # tên thương hiệu nếu có
    corePromise: Optional[str]           # Lời hứa thương hiệu
    brandManifesto: Optional[str]        # WHY cảm xúc
    brandPersona: Optional[str]          # ví dụ: người anh, bạn thân, chuyên gia
    keyMessages: List[str]               # Những thông điệp chính cần lặp lại
    callsToAction: List[str]             # CTA: mua ngay, chia sẻ, comment...

    # Phân tích hệ thống
    confidenceScore: int                 # đánh giá độ đầy đủ input (0-100)

class DescriptionGenerate(BaseModel):
    campaign_meta: DescriptionPrompt



async def generate_campaign_meta(campaign: CampaignInput, db: Session) -> DescriptionGenerate:
    """Generate campaign metadata in background"""
    start_time = time.time()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    print(f"🏁 Background task bắt đầu lúc: {time.strftime('%H:%M:%S')}")
    
    print('Generating campaign metadata', campaign.model_dump())
    system_prompt = """
            Bạn là AI chuyên phân tích nội dung tự nhiên từ người dùng để phân loại các yếu tố sau cho một chiến dịch marketing.
            Hãy phân tích chiến dịch và trả về định dạng JSON như sau:

            {{
            "description": {{
                # Phong cách và mục tiêu nội dung
                "toneWriting": "string",           # Ví dụ: ấm áp, chuyên nghiệp, hài hước
                "topicStyle": "string",            # storytelling, quote, case study
                "platforms": ["string"],           # ["Facebook", "TikTok"]
                "imageMood": "string",             # Ví dụ: thư giãn, năng lượng, ấm áp
                "mindset": "string",               # học hỏi, giải trí, truyền cảm hứng
                "contentObjective": "string",      # Mục tiêu: bán hàng, nhận diện, kích hoạt

                # Khách hàng mục tiêu
                "targetCustomer": "string",        # mô tả người mua lý tưởng
                "painPoints": ["string"],          # các rào cản / lo lắng thường gặp
                "bigKeywords": ["string"],         # từ khóa sản phẩm / insight tìm kiếm

                # Định vị thương hiệu
                "brandName": "string",             # tên thương hiệu nếu có
                "corePromise": "string",           # Lời hứa thương hiệu
                "brandManifesto": "string",        # WHY cảm xúc
                "brandPersona": "string",          # ví dụ: người anh, bạn thân, chuyên gia
                "keyMessages": ["string"],         # Những thông điệp chính cần lặp lại
                "callsToAction": ["string"],       # CTA: mua ngay, chia sẻ, comment...

                # Phân tích hệ thống
                "confidenceScore": 100             # đánh giá độ đầy đủ input (0-100)
            }}
            }}

           
            """

    # Use asyncio.create_task to run in true background
    response = await client.aio.models.generate_content(
        # model='gemini-2.0-flash',
        model='gemini-2.5-flash-preview-04-17',
        contents=f"""Phân tích thông tin chiến dịch để xác định các yếu tố description prompt.  Tiêu đề: {campaign.title}
            Mô tả: {campaign.description}
            Đối tượng: {campaign.targetCustomer}
            Insight: {campaign.insight}""",
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=DescriptionGenerate,
            system_instruction=Part(text=system_prompt)
        )
    )

    print("✅ Đã phân tích thông tin chiến dịch.")
    content = json.loads(response.text)
    
    if campaign.id:
        # Update existing campaign
        existing_campaign = db.query(Campaign).filter(Campaign.id == campaign.id).first()
        if existing_campaign:
            existing_campaign.campaign_data = content
            existing_campaign.title = campaign.title
            existing_campaign.description = campaign.description
            existing_campaign.target_customer = campaign.targetCustomer
            existing_campaign.insight = campaign.insight
            db.commit()
            print(f"✅ Đã cập nhật campaign data cho chiến dịch ID {campaign.id}")
            return DescriptionGenerate(**content)
    
    # # Create new campaign if no ID or campaign not found
    # new_campaign = Campaign(
    #     title=campaign.title,
    #     description=campaign.description,
    #     target_customer=campaign.targetCustomer,
    #     insight=campaign.insight,
    #     campaign_data=content,
    #     repeat_every_days=7,
    #     current_step=1
    # )
    
    # db.add(new_campaign)
    # db.commit()
    # db.refresh(new_campaign)
    
    print(f"✅ Đã lưu campaign data mới cho chiến dịch: {campaign.title}")

    return DescriptionGenerate(**content)

@router.post("/gen_campaign_system")
async def generate_campaign_system(req: CampaignRequest, db: Session = Depends(get_db)):
    import asyncio
    
    start_time = time.time()
    campaign = req.campaignInput
    print(campaign.model_dump())
    try:
        # Create a true background task using asyncio
        task = asyncio.create_task(generate_campaign_meta(campaign, db))
        
        end_time = time.time()
        route_execution_time = end_time - start_time
        
        return {
            "message": "Campaign analysis started in background",
            "campaign": campaign.model_dump(),
            "status": "processing",
            "route_execution_time": f"{route_execution_time:.2f} seconds"
        }

    except Exception as e:
        logging.exception("❌ Error generating campaign system prompt")
        raise HTTPException(status_code=500, detail=str(e))

