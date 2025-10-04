from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, Literal

class CandidateBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    mobile: Optional[str] = None
    job_title: Optional[str] = None
    address: Optional[str] = None

class CandidateCreate(CandidateBase):
    pass

class CandidateOut(CandidateBase):
    id: int
    status: str
    applied_on: datetime

    class Config:
        from_attributes = True

###

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str



### Candidate Profile Schemas
class CandidateProfileBase(BaseModel):
    summary: Optional[str] = None
    skills: Optional[str] = None
    linkedin: Optional[str] = None
    address: Optional[str] = None

class CandidateProfileUpdate(CandidateProfileBase):
    pass

class CandidateProfileOut(CandidateProfileBase):
    id: int
    resume_path: Optional[str] = None
    photo_path: Optional[str] = None
    # When returned as JSON
    class Config:
        from_attributes = True

# Input when create offer
class OfferCreate(BaseModel):
    candidate_id: int
    job_title: str
    salary: Optional[str] = None
    start_date: Optional[datetime] = None
    expire_at: Optional[datetime] = None  

# Offer info
class OfferOut(BaseModel):
    id: int
    candidate_id: int
    job_title: str
    salary: Optional[str] = None
    start_date: Optional[datetime] = None
    expire_at: Optional[datetime] = None
    status: Literal["Draft", "Sent", "Signed", "Expired", "Cancelled"]  
    pdf_path: Optional[str] = None
    signed_pdf_path: Optional[str] = None
    signed_at: Optional[datetime] = None
    signed_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  

class OfferSignIn(BaseModel):
    signer_name: str
