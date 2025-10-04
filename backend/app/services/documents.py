# backend/app/services/documents.py
from __future__ import annotations

from pathlib import Path
from typing import Optional
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/app
BACKEND_DIR = BASE_DIR.parent                      # backend
TEMPLATES_DIR = BACKEND_DIR / "templates" / "offers"
OUTPUT_DIR = BACKEND_DIR / "generated" / "offers"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"])
)

# date format
def _date_au(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    return dt.strftime("%d %b %Y")

env.filters["date_au"] = _date_au


def render_offer_html(template_name: str, context: dict) -> str:
    # avoid path cross
    if "/" in template_name or "\\" in template_name:
        raise ValueError("template_name should be a plain file name like 'offer_default.html'")
    template = env.get_template(template_name)
    return template.render(**context)


def save_offer_html(offer_id: int, html: str, *, suffix: str = "") -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{suffix}" if suffix else ""
    path = OUTPUT_DIR / f"offer_{offer_id}{suffix}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


def html_to_pdf(html_path: str) -> Optional[str]:
    pdf_path = html_path.replace(".html", ".pdf") #transfer html to pdf
    try:
        from weasyprint import HTML  # type: ignore
        HTML(filename=html_path).write_pdf(pdf_path)
        return pdf_path
    except Exception:
        pass
    try:
        import pdfkit  # type: ignore
        pdfkit.from_file(html_path, pdf_path)
        return pdf_path
    except Exception:
        return None


def append_signature_footer(html: str, *, signer_name: str, signed_at: datetime, ip: Optional[str]) -> str:
    #generate a "signed version"
    footer = f"""  
    <hr/>
    <div style="font-size:12px;color:#444;margin-top:16px;">
      <strong>Electronically signed by:</strong> {signer_name}<br/>
      <strong>Date (UTC):</strong> {signed_at.strftime("%Y-%m-%d %H:%M:%S")}<br/>
      <strong>IP:</strong> {ip or "-"}<br/>
    </div>
    """
    lower = html.lower()
    insert_at = lower.rfind("</body>")
    if insert_at != -1:
        return html[:insert_at] + footer + html[insert_at:]
    return html + footer


def generate_original_files(
    *,
    offer_id: int,
    template_name: str = "offer_default.html",
    context: dict
) -> tuple[str, Optional[str]]:
    html = render_offer_html(template_name, context)
    html_path = save_offer_html(offer_id, html, suffix="orig")
    pdf_path = html_to_pdf(html_path)
    return html_path, pdf_path


def generate_signed_files(
    *,
    offer_id: int,
    original_html_path: str,
    signer_name: str,
    signed_at: datetime,
    ip: Optional[str]
) -> tuple[str, Optional[str]]:
    src = Path(original_html_path) #create signed version
    html = src.read_text(encoding="utf-8")
    signed_html = append_signature_footer(html, signer_name=signer_name, signed_at=signed_at, ip=ip)
    signed_html_path = save_offer_html(offer_id, signed_html, suffix="signed")
    signed_pdf_path = html_to_pdf(signed_html_path)
    return signed_html_path, signed_pdf_path
