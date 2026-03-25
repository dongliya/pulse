from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.db import get_db
router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[schemas.ProjectSummary])
def read_projects(db: Session = Depends(get_db)):
    return crud.list_projects(db)


@router.get("/{project_name}")
def read_project(project_name: str, include_reports: bool = Query(default=True), db: Session = Depends(get_db)):
    project_detail = crud.get_project_detail_payload(db, project_name)
    if project_detail is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if include_reports:
        return project_detail
    return {"summary": project_detail["summary"]}
