from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Request
from sqlalchemy.orm import Session
import os
from datetime import datetime
from app.database import get_db
from app import schemas, models
from app import crud
from app.services.documents import generate_original_files
from app.services import mailer

router = APIRouter()

@router.post("/admin/offers", response_model=schemas.OfferOut)
def create_and_send_offer(
    data: schemas.OfferCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    #Validate if candidate in the db
    candidate = db.query(models.Candidate).filter(models.Candidate.id == data.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    #Crreate the ooffer
    offer = crud.create_offer(db, data)

    #渲染并生成原版文件
    context = {
        "candidate_name": getattr(candidate, "full_name", getattr(candidate, "name", "Candidate")),
        "job_title": data.job_title,
        "salary": data.salary,
        "start_date": data.start_date,
        "offer_valid_until": data.expire_at,
        "company_name": os.getenv("COMPANY_NAME", "Your Company"),
        "location": os.getenv("COMPANY_LOCATION", "Melbourne"),
        "hr_contact_name": os.getenv("EMAIL_FROM_NAME", "HR Team"),
        "hr_contact_email": os.getenv("SMTP_USER", "hr@example.com"),
        "offer_id": offer.id,
        "now": datetime.utcnow(),
    }
    orig_html_path, orig_pdf_path = generate_original_files(
        offer_id=offer.id, template_name="offer_default.html", context=context
    )

    #把   HTML 内容也写回
    html_body = None
    try:
        with open(orig_html_path, "r", encoding="utf-8") as f:
            html_body = f.read()
    except Exception:
        pass

    offer = crud.update_offer_files(db, offer_id=offer.id, html_body=html_body, pdf_path=orig_pdf_path)

    # 5) Create one time sign token
    raw_token = crud.create_signature_token(db, offer_id=offer.id, ttl_hours=int(os.getenv("OFFER_TOKEN_TTL_HOURS", "72")))
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    offer_link = f"{base_url}/api/offers/preview?token={raw_token}"  

    #MArk as SENT
    offer = crud.mark_offer_sent(db, offer.id)

    #异步发信
    to_email = getattr(candidate, "email", None) or os.getenv("DEV_FALLBACK_EMAIL", "")
    if to_email:
        background_tasks.add_task(
            mailer.send_offer_email,
            to_email=to_email,
            candidate_name=context["candidate_name"],
            offer_link=offer_link,
            company_name=os.getenv("COMPANY_NAME"),
            expire_at=data.expire_at,
        )
    else:
        # 无收件人就跳过发信，避免后台任务报错
        print("[offers] skip sending email: no candidate.email and no DEV_FALLBACK_EMAIL")


    return offer
