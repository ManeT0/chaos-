from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.db import get_db, Team, User, TeamMembership
from backend.auth import require_role

router = APIRouter(prefix="/api/teams", tags=["teams"])

@router.get("/")
def list_teams(db: Session = Depends(get_db), current_user: User = Depends(require_role(["admin"]))):
    teams = db.query(Team).all()
    return [{"id": t.id, "name": t.name} for t in teams]

@router.post("/")
def create_team(name: str, db: Session = Depends(get_db), current_user: User = Depends(require_role(["admin"]))):
    team = Team(name=name)
    db.add(team)
    db.commit()
    db.refresh(team)
    return {"id": team.id, "name": team.name}

@router.post("/{team_id}/members")
def add_team_member(team_id: int, user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(["admin"]))):
    membership = TeamMembership(team_id=team_id, user_id=user_id)
    db.add(membership)
    db.commit()
    return {"message": "Member added"}
