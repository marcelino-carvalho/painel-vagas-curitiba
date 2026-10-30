"""
Serviço de geração de PDF em alta resolução (A4 Paisagem) utilizando Playwright Chromium.
Garante fidelidade visual ao modelo de referência, responsividade de página única (até ~65-70 empresas)
e paginação automática inteligente caso o volume de empresas/vagas ultrapasse uma página.
"""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Any, List, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from app.default_logo import DEFAULT_LOGO_DATA_URL
from app.qr_service import generate_qr_png_data_url

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

_pdf_executor = ThreadPoolExecutor(max_workers=2)


def render_pdf_html(
    title: str,
    companies: List[Dict[str, Any]],
    public_url: str,
    logo_data_url: Optional[str] = None,
    header_style: str = "dark",
) -> str:
    """Renderiza o HTML dedicado para exportação A4 Paisagem."""
    qr_data_url = generate_qr_png_data_url(public_url, box_size=10, border=1)
    final_logo = logo_data_url if logo_data_url else DEFAULT_LOGO_DATA_URL

    payload = {
        "title": title,
        "companies": companies,
        "public_url": public_url,
        "logo_data_url": final_logo,
        "qr_data_url": qr_data_url,
        "header_style": header_style or "dark",
    }

    template = _jinja_env.get_template("pdf_template.html")
    return template.render(
        title=title,
        header_style=header_style or "dark",
        payload_json=json.dumps(payload, ensure_ascii=False),
    )


def _generate_pdf_bytes_sync(html_content: str) -> bytes:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1400, "height": 990})
            page.set_content(html_content, wait_until="load")
            page.wait_for_function("window.__PDF_LAYOUT_READY__ === true", timeout=10000)
            pdf_bytes = page.pdf(
                format="A4",
                landscape=True,
                print_background=True,
                 prefer_css_page_size=True,
                margin={"top": "5mm", "right": "5mm", "bottom": "5mm", "left": "5mm"},
            )
            return pdf_bytes
        finally:
            browser.close()


async def generate_panel_pdf(
    title: str,
    companies: List[Dict[str, Any]],
    public_url: str,
    logo_data_url: Optional[str] = None,
    header_style: str = "dark",
) -> bytes:
    """Gera o arquivo PDF em bytes de forma assíncrona."""
    html_content = render_pdf_html(
        title=title,
        companies=companies,
        public_url=public_url,
        logo_data_url=logo_data_url,
        header_style=header_style,
    )
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_pdf_executor, _generate_pdf_bytes_sync, html_content)
