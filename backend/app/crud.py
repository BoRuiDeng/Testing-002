from sqlalchemy.orm import Session
from . import models, schemas
from passlib.context import CryptContext
from typing import Optional
from datetime import datetime, timedelta
import hashlib, secrets

def create_candidate(db: Session, candidate: schemas.CandidateCreate, user_id: int | None = None):
    db_candidate = models.Candidate(
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        email=candidate.email,
        mobile=candidate.mobile,
        job_title=candidate.job_title,
        address=candidate.address,
        status="Applied",
        user_id=user_id
    )
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    return db_candidate

def get_candidate(db: Session, candidate_id: int):
    return db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()

def get_candidates(db: Session, skip: int = 0, limit: int = 10):
    return db.query(models.Candidate).offset(skip).limit(limit).all()

##

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_user(db: Session, user: schemas.UserCreate):
    hashed_pw = get_password_hash(user.password)
    db_user = models.User(username=user.username, email=user.email, hashed_password=hashed_pw)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


## Candidate Profile CRUD
def get_candidate_by_user(db: Session, user_id: int):
    return db.query(models.Candidate).filter(models.Candidate.user_id == user_id).first()

def get_profile(db: Session, candidate_id: int):
    return db.query(models.CandidateProfile).filter(models.CandidateProfile.candidate_id == candidate_id).first()

def get_or_create_profile(db: Session, candidate_id: int):
    prof = get_profile(db, candidate_id)
    if prof:
        return prof
    prof = models.CandidateProfile(candidate_id=candidate_id)
    db.add(prof)
    db.commit()
    db.refresh(prof)
    return prof

def update_profile(db: Session, candidate_id: int, data: "schemas.CandidateProfileUpdate"):
    prof = get_or_create_profile(db, candidate_id)
    for field, value in data.dict(exclude_unset=True).items():
        setattr(prof, field, value)
    db.add(prof)
    db.commit()
    db.refresh(prof)
    return prof

def set_profile_file(db: Session, candidate_id: int, kind: str, path: str):
    prof = get_or_create_profile(db, candidate_id)
    if kind == "resume":
        prof.resume_path = path
    elif kind == "photo":
        prof.photo_path = path
    else:
        raise ValueError("kind must be 'resume' or 'photo'")
    db.add(prof)
    db.commit()
    db.refresh(prof)
    return prof


def create_offer(
    db: Session,
    data: schemas.OfferCreate,
    html_body: Optional[str] = None,
    pdf_path: Optional[str] = None,
) -> models.Offer:
    candidate = db.query(models.Candidate).filter(models.Candidate.id == data.candidate_id).first()
    if not candidate:
        raise ValueError(f"Candidate {data.candidate_id} not found")

    offer = models.Offer(
        candidate_id=data.candidate_id,
        job_title=data.job_title,
        salary=data.salary,
        start_date=data.start_date,
        expire_at=data.expire_at,
        status=models.OfferStatus.DRAFT,
        html_body=html_body,
        pdf_path=pdf_path,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def mark_offer_sent(db: Session, offer_id: int) -> models.Offer:
    """Mark the Offer (SENT）。"""
    offer = db.query(models.Offer).filter(models.Offer.id == offer_id).first()
    if not offer:
        raise ValueError(f"Offer {offer_id} not found")
    offer.status = models.OfferStatus.SENT
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def mark_offer_signed(
    db: Session,
    offer_id: int,
    signer_name: str,
    signed_pdf_path: Optional[str] = None,
) -> models.Offer:
    """Offer SIGNED。"""
    offer = db.query(models.Offer).filter(models.Offer.id == offer_id).first()
    if not offer:
        raise ValueError(f"Offer {offer_id} not found")
    offer.status = models.OfferStatus.SIGNED
    offer.signed_at = datetime.utcnow()
    offer.signed_by_name = signer_name
    if signed_pdf_path:
        offer.signed_pdf_path = signed_pdf_path
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def get_offer_by_id(db: Session, offer_id: int) -> Optional[models.Offer]:
    return db.query(models.Offer).filter(models.Offer.id == offer_id).first()


def list_offers(
    db: Session,
    *,
    status: Optional[models.OfferStatus] = None,
    candidate_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.Offer]:
    q = db.query(models.Offer)
    if status:
        q = q.filter(models.Offer.status == status)
    if candidate_id:
        q = q.filter(models.Offer.candidate_id == candidate_id)
    return q.order_by(models.Offer.id.desc()).offset(offset).limit(limit).all()


# Sign token

def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_signature_token(
    db: Session,
    offer_id: int,
    ttl_hours: int = 72,
) -> str:

    offer = db.query(models.Offer).filter(models.Offer.id == offer_id).first()
    if not offer:
        raise ValueError(f"Offer {offer_id} not found")

    raw = secrets.token_urlsafe(24)
    token = models.OfferSignatureToken(
        offer_id=offer_id,
        token_hash=_hash_token(raw),
        expires_at=datetime.utcnow() + timedelta(hours=ttl_hours),
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return raw  


def verify_and_consume_token(
    db: Session,
    raw_token: str,
) -> Optional[models.OfferSignatureToken]:

    token_hash = _hash_token(raw_token)
    tok = (
        db.query(models.OfferSignatureToken)
        .filter(models.OfferSignatureToken.token_hash == token_hash)
        .first()
    )
    if not tok:
        return None
    if tok.used_at is not None:
        return None
    if tok.expires_at < datetime.utcnow():
        return None

    tok.used_at = datetime.utcnow()
    db.add(tok)
    db.commit()
    db.refresh(tok)
    return tok

def update_offer_files(
    db: Session,
    *,
    offer_id: int,
    html_body: str | None = None,
    pdf_path: str | None = None,
) -> models.Offer:
    offer = db.query(models.Offer).filter(models.Offer.id == offer_id).first()
    if not offer:
        raise ValueError(f"Offer {offer_id} not found")

    if html_body is not None:
        offer.html_body = html_body
    if pdf_path is not None:
        offer.pdf_path = pdf_path

    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer

