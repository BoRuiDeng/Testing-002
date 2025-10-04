from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum, Text
from sqlalchemy.sql import func
from .database import Base
from datetime import datetime, timedelta

class OfferStatus(str, enum.Enum):
    DRAFT = "Draft"
    SENT = "Sent"
    SIGNED = "Signed"
    EXPIRED = "Expired"
    CANCELLED = "Cancelled"

class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True, index=True)
    mobile: Mapped[str | None]
    job_title: Mapped[str | None]
    address: Mapped[str | None]

    status: Mapped[str] = mapped_column(default="Applied")
    applied_on: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="candidates")
    profile: Mapped["CandidateProfile"] = relationship(back_populates="candidate", uselist=False, cascade="all, delete-orphan")

    offers: Mapped[list["Offer"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]

    candidates: Mapped[list["Candidate"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), unique=True)

    summary: Mapped[str | None]
    skills: Mapped[str | None]
    linkedin: Mapped[str | None]
    address: Mapped[str | None]
    resume_path: Mapped[str | None]
    photo_path: Mapped[str | None]

    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    candidate: Mapped["Candidate"] = relationship(back_populates="profile")

class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)

    # 业务字段（可按需精简/扩展）
    job_title: Mapped[str] = mapped_column(String(200))
    salary: Mapped[str | None] = mapped_column(String(100))         
    start_date: Mapped[datetime | None]
    expire_at: Mapped[datetime | None]                               # 签署截止时间

    status: Mapped[OfferStatus] = mapped_column(Enum(OfferStatus), default=OfferStatus.DRAFT, nullable=False)

    # 审计/存档
    html_body: Mapped[str | None] = mapped_column(Text)
    pdf_path: Mapped[str | None] = mapped_column(String(500))        # 未签署版 PDF 路径
    signed_pdf_path: Mapped[str | None] = mapped_column(String(500)) # 已签署版 PDF 路径
    signed_at: Mapped[datetime | None]
    signed_by_name: Mapped[str | None] = mapped_column(String(200))  # 候选人输入的签名名（简化 e-sign）

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    candidate: Mapped["Candidate"] = relationship(back_populates="offers")


class OfferSignatureToken(Base):
    __tablename__ = "offer_signature_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), index=True)

    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None]

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    offer: Mapped["Offer"] = relationship()
