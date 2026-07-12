from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.db import get_db, Project, User
from backend.auth import get_current_user, require_team_access

router = APIRouter(prefix="/api/projects", tags=["projects"])

@router.get("/")
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "admin":
        projects = db.query(Project).all()
    else:
        team_ids = [tm.team_id for tm in current_user.teams]
        projects = db.query(Project).filter(Project.team_id.in_(team_ids)).all()
    return [{"id": p.id, "name": p.name, "team_id": p.team_id} for p in projects]

@router.post("/")
def create_project(name: str, team_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if user is admin or belongs to team
    if current_user.role != "admin" and team_id not in [tm.team_id for tm in current_user.teams]:
        raise HTTPException(status_code=403, detail="Not authorized to create project for this team")
        
    project = Project(name=name, team_id=team_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"id": project.id, "name": project.name, "team_id": project.team_id}
