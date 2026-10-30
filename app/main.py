"""
Aplicação Principal FastAPI — Sistema de Criação de Painel de Vagas
Agência do Trabalhador de Curitiba
"""

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.database import (
    get_panel_by_slug,
    init_db,
    list_recent_panels,
    save_or_update_panel,
)
from app.default_logo import DEFAULT_LOGO_DATA_URL
from app.parser import SAMPLE_MUTIRAO_TEXT, parse_vagas_text
from app.pdf_service import generate_panel_pdf
from app.qr_service import generate_qr_png_data_url
from app.tunnel import (
    get_current_tunnel_status,
    get_public_base_url,
    start_public_tunnel,
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

INITIAL_STARTER_TEXT = """EMPRESA A
Auxiliar Administrativo
Operador de Caixa
Atendente de Loja
Vendedor Externo

EMPRESA B
Auxiliar de Produção
Operador de Máquinas

EMPRESA C
Motorista
Auxiliar de Logística
Analista Administrativo"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    port = int(os.environ.get("PORT", "8000"))
    is_cloud_hosted = bool(
        os.environ.get("PUBLIC_BASE_URL")
        or os.environ.get("RENDER")
        or os.environ.get("RENDER_EXTERNAL_URL")
        or os.environ.get("RAILWAY_ENVIRONMENT")
    )
    if not is_cloud_hosted:
        start_public_tunnel(local_port=port)
    yield


app = FastAPI(
    title="Painel de Vagas — Agência do Trabalhador de Curitiba",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class ParseRequest(BaseModel):
    raw_text: str


class PublishPanelRequest(BaseModel):
    title: str
    raw_text: str
    slug: Optional[str] = None
    logo_data_url: Optional[str] = None
    header_style: str = "dark"


def _resolve_public_panel_url(request: Request, slug: str) -> str:
    port = int(os.environ.get("PORT", "8000"))
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    forwarded_proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    base_url = get_public_base_url(
        request_host=forwarded_host,
        request_scheme=forwarded_proto,
        local_port=port,
    )
    return f"{base_url}/p/{slug}"


@app.get("/", response_class=HTMLResponse)
async def admin_index(request: Request):
    recent = list_recent_panels(limit=1)
    if recent:
        initial_panel = recent[0]
    else:
        initial_panel = save_or_update_panel(
            title="MUTIRÃO EMPREGA + [NOME DO EVENTO] | CASA DO TRABALHADOR",
            raw_text=INITIAL_STARTER_TEXT,
            slug="mutirao-emprega-curitiba",
            header_style="dark",
        )

    public_url = _resolve_public_panel_url(request, initial_panel["slug"])
    qr_data_url = generate_qr_png_data_url(public_url)

    boot_payload = {
        "initial_slug": initial_panel["slug"],
        "initial_public_url": public_url,
        "initial_qr_data_url": qr_data_url,
        "default_logo_data_url": DEFAULT_LOGO_DATA_URL,
        "sample_65_text": SAMPLE_MUTIRAO_TEXT,
    }

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "initial_raw_text": initial_panel["raw_text"],
            "initial_public_url": public_url,
            "default_logo_data_url": DEFAULT_LOGO_DATA_URL,
            "boot_json": json.dumps(boot_payload, ensure_ascii=False),
        },
    )


@app.get("/p/{slug}", response_class=HTMLResponse)
async def public_panel_view(request: Request, slug: str):
    panel = get_panel_by_slug(slug)
    if not panel:
        raise HTTPException(status_code=404, detail="Painel de vagas não encontrado.")

    return templates.TemplateResponse(
        request=request,
        name="public_panel.html",
        context={
            "panel": panel,
            "default_logo": DEFAULT_LOGO_DATA_URL,
        },
    )


@app.post("/api/parse")
async def api_parse_text(payload: ParseRequest):
    return parse_vagas_text(payload.raw_text)


@app.post("/api/panels")
async def api_publish_panel(request: Request, payload: PublishPanelRequest):
    parsed = parse_vagas_text(payload.raw_text)
    if parsed["total_companies"] == 0:
        raise HTTPException(
            status_code=400,
            detail="Informe pelo menos uma empresa no campo de texto antes de publicar.",
        )

    saved = save_or_update_panel(
        title=payload.title,
        raw_text=payload.raw_text,
        slug=payload.slug,
        logo_data_url=payload.logo_data_url,
        header_style=payload.header_style,
    )

    public_url = _resolve_public_panel_url(request, saved["slug"])
    qr_data_url = generate_qr_png_data_url(public_url)

    return {
        **saved,
        "public_url": public_url,
        "qr_data_url": qr_data_url,
    }


@app.get("/api/panels/{slug}")
async def api_get_panel(request: Request, slug: str):
    panel = get_panel_by_slug(slug)
    if not panel:
        raise HTTPException(status_code=404, detail="Painel não encontrado.")

    public_url = _resolve_public_panel_url(request, panel["slug"])
    qr_data_url = generate_qr_png_data_url(public_url)

    return {
        **panel,
        "public_url": public_url,
        "qr_data_url": qr_data_url,
    }


@app.get("/api/panels/{slug}/pdf")
async def api_export_panel_pdf(request: Request, slug: str):
    panel = get_panel_by_slug(slug)
    if not panel:
        raise HTTPException(status_code=404, detail="Painel não encontrado para exportação PDF.")

    public_url = _resolve_public_panel_url(request, panel["slug"])
    pdf_bytes = await generate_panel_pdf(
        title=panel["title"],
        companies=panel["companies"],
        public_url=public_url,
        logo_data_url=panel["logo_data_url"],
        header_style=panel["header_style"],
    )

    filename = f"painel-vagas-{panel['slug']}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@app.get("/api/status")
async def api_status(request: Request):
    tunnel_info = get_current_tunnel_status()
    return {
        "status": "ok",
        **tunnel_info,
    }
