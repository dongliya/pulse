from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.db import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=schemas.DashboardSummary)
def read_dashboard(db: Session = Depends(get_db)):
    return crud.get_dashboard_summary(db)
