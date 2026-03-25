from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.db import get_db

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=list[schemas.ReportRead])
def read_activities(db: Session = Depends(get_db)):
    return crud.list_activities(db)


@router.post("", response_model=schemas.ReportRead, status_code=status.HTTP_201_CREATED)
def create_activity(payload: schemas.ReportCreate, db: Session = Depends(get_db)):
    return crud.create_activity(db, payload)


@router.get("/{activity_id}", response_model=schemas.ReportRead)
def read_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = crud.get_activity(db, activity_id)
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    return activity


@router.put("/{activity_id}", response_model=schemas.ReportRead)
def update_activity(activity_id: int, payload: schemas.ReportUpdate, db: Session = Depends(get_db)):
    activity = crud.get_activity(db, activity_id)
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    return crud.update_activity(db, activity, payload)


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = crud.get_activity(db, activity_id)
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    crud.delete_activity(db, activity)
