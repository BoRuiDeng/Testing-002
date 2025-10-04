from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import os
from pathlib import Path

from .. import models, schemas, crud, database

router = APIRouter(prefix="/portal", tags=["portal"])
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def get_current_user(request: Request, db: Session = Depends(database.get_db)) -> models.User:
    user = request.session.get("user")
    if not user:
        # Not logged in
        raise HTTPException(status_code=401, detail="Not authenticated")
    db_user = db.query(models.User).filter(models.User.id == user["id"]).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")
    return db_user


@router.get("/profile", response_class=HTMLResponse)
def profile_form(
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    candidate = crud.get_candidate_by_user(db, user_id=int(current_user.id))
    if not candidate:
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "user": current_user, "error": "No candidate record associated with this account."},
        )
    profile = crud.get_or_create_profile(db, candidate.id)
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "user": current_user, "candidate": candidate, "profile": profile},
    )


@router.post("/profile", response_class=HTMLResponse)
def profile_submit(
    request: Request,
    summary: Optional[str] = Form(None),
    skills: Optional[str] = Form(None),
    linkedin: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    job_title: Optional[str] = Form(None),   # <-- NEW: role/title field
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    candidate = crud.get_candidate_by_user(db, user_id=int(current_user.id))
    if not candidate:
        raise HTTPException(status_code=400, detail="No candidate linked to this user")

    # Update Candidate.job_title (Role)
    candidate.job_title = (job_title or "").strip()
    db.add(candidate)

    # Update CandidateProfile fields
    update = schemas.CandidateProfileUpdate(
        summary=summary, skills=skills, linkedin=linkedin, address=address
    )
    profile = crud.update_profile(db, candidate.id, update)

    db.commit()
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "user": current_user, "candidate": candidate, "profile": profile, "saved": True},
    )


@router.post("/profile/upload")
async def upload_file(
    request: Request,
    kind: str = Form(...),  # 'resume' or 'photo'
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    if kind not in {"resume", "photo"}:
        raise HTTPException(status_code=400, detail="kind must be 'resume' or 'photo'")
    candidate = crud.get_candidate_by_user(db, user_id=int(current_user.id))
    if not candidate:
        raise HTTPException(status_code=400, detail="No candidate linked to this user")

    filename = file.filename or ""
    ext = os.path.splitext(filename)[1] or (".png" if kind == "photo" else ".pdf")

    # Save under uploads/{candidate_id}/
    folder = UPLOAD_DIR / str(candidate.id)
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{kind}{ext}"
    with open(dest, "wb") as f:
        f.write(await file.read())

    _prof = crud.set_profile_file(db, candidate.id, kind, str(dest))
    return RedirectResponse(url="/portal/profile", status_code=303)


@router.get("/profile/admin/{user_id}", response_class=HTMLResponse)
def profile_admin(user_id: int, request: Request, db: Session = Depends(database.get_db)):
    # Admin view of a user's profile (no session requirement)
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    candidate = crud.get_candidate_by_user(db, user_id=int(db_user.id))
    if not candidate:
        return templates.TemplateResponse(
            "profile.html",
            {
                "request": request,
                "user": db_user,
                "candidate": None,
                "profile": None,
                "admin_view": True,
                "error": "No candidate record linked to this user.",
            },
        )
    profile = crud.get_or_create_profile(db, candidate.id)
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "user": db_user, "candidate": candidate, "profile": profile, "admin_view": True},
    )


@router.post("/profile/admin/{user_id}")
def admin_save_profile(
    user_id: int,
    request: Request,
    summary: Optional[str] = Form(None),
    skills: Optional[str] = Form(None),
    linkedin: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    job_title: Optional[str] = Form(None),   # <-- NEW: role/title field
    db: Session = Depends(database.get_db),
):
    # Locate the target user
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Ensure a candidate exists (create if missing to allow admin editing)
    candidate = crud.get_candidate_by_user(db, user_id=int(db_user.id))
    if not candidate:
        candidate = models.Candidate(
            user_id=db_user.id,
            email=db_user.email or "",
            first_name="",
            last_name="",
            status="Applied",
        )
        db.add(candidate)
        db.flush()

    # Update Candidate.job_title (Role)
    candidate.job_title = (job_title or "").strip()
    db.add(candidate)

    # Ensure profile exists and update profile fields
    _ = crud.get_or_create_profile(db, candidate.id)
    update = schemas.CandidateProfileUpdate(
        summary=summary, skills=skills, linkedin=linkedin, address=address
    )
    profile = crud.update_profile(db, candidate.id, update)

    db.commit()
    # Redirect back to the admin view (shows "saved" banner if you want to check query param)
    return RedirectResponse(url=f"/portal/profile/admin/{db_user.id}?saved=1", status_code=303)
