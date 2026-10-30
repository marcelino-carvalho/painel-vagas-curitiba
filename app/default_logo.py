"""
Logotipo institucional padrão para o cabeçalho do painel e do PDF
(PARANÁ GOVERNO DO ESTADO — SECRETARIA DO TRABALHO, QUALIFICAÇÃO E RENDA).
Carrega a imagem oficial em static/img/logo-parana-pdf.png.
"""

import base64
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LOGO_PATH = BASE_DIR / "static" / "img" / "logo-parana-pdf.png"
BRASAO_SITE_URL = "/static/img/brasao-parana.png"


def _load_default_logo_data_url() -> str:
    if DEFAULT_LOGO_PATH.exists():
        raw = DEFAULT_LOGO_PATH.read_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        return f"data:image/png;base64,{b64}"
    return ""


DEFAULT_LOGO_DATA_URL = _load_default_logo_data_url()
