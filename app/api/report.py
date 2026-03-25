from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.db import get_db

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[schemas.ReportRead], include_in_schema=False)
def read_reports(db: Session = Depends(get_db)):
    return crud.list_activities(db)


@router.post("", response_model=schemas.ReportRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_report(payload: schemas.ReportCreate, db: Session = Depends(get_db)):
    return crud.create_activity(db, payload)


@router.get("/{report_id}", response_model=schemas.ReportRead, include_in_schema=False)
def read_report(report_id: int, db: Session = Depends(get_db)):
    report = crud.get_activity(db, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    return report


@router.put("/{report_id}", response_model=schemas.ReportRead, include_in_schema=False)
def update_report(report_id: int, payload: schemas.ReportUpdate, db: Session = Depends(get_db)):
    report = crud.get_activity(db, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    return crud.update_activity(db, report, payload)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = crud.get_activity(db, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    crud.delete_activity(db, report)
