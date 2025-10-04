# app/routers/candidates.py

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app import models

router = APIRouter()

# --- payload model the frontend sends ---
class CandidateCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    mobile: Optional[str] = None
    job_title: Optional[str] = None
    address: Optional[str] = None
    applied_on: Optional[date] = None  # optional; DB default handles if omitted


# --- JSON API used by the intake form ---
@router.post("/api/v1/hr/recruitment/candidates/", response_class=JSONResponse)
def api_create_candidate(
    payload: CandidateCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    # must be logged in to attach user_id
    session_user = request.session.get("user")
    if not session_user:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    try:
        cand = models.Candidate(
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            mobile=payload.mobile or "",
            job_title=payload.job_title or "",
            address=payload.address or "",
            status="Applied",
            user_id=session_user["id"],  # REQUIRED by your schema
            # applied_on: DB server_default handles this if not provided
        )
        db.add(cand)
        db.commit()
        db.refresh(cand)
        return JSONResponse({"id": cand.id, "detail": "created"}, status_code=201)
    except IntegrityError:
        db.rollback()
        return JSONResponse({"detail": "Email already exists for a candidate."}, status_code=409)
