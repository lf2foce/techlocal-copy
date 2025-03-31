from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.db import get_db
from services.scheduler import run_daily_schedule

router = APIRouter(prefix="/scheduled_posts", tags=["Scheduler"])

@router.post("/daily_trigger")
def trigger_daily_schedule(db: Session = Depends(get_db)):
    count = run_daily_schedule(db)
    return {"message": f"{count} post(s) sent today."}