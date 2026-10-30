"""
Serviço de geração de PDF em alta resolução (A4 Paisagem) 100% nativo em Python (ReportLab).
Não depende de navegador headless (Chromium/Playwright), consome menos de 15 MB de RAM
e funciona perfeitamente em qualquer hospedagem (incluindo Render Free Tier, Railway, Fly.io e Windows/Linux).
"""

import base64
import io
import math
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from app.qr_service import generate_qr_png_data_url

PAGE_W, PAGE_H = landscape(A4)  # 841.89 x 595.27 pt (297mm x 210mm)
MARGIN = 5 * mm
SHEET_W = PAGE_W - 2 * MARGIN
SHEET_H = PAGE_H - 2 * MARGIN
COLS = 7


def _wrap_text(text: str, font_name: str, font_size: float, max_width: float) -> List[str]:
    """Quebra um texto em múltiplas linhas para caber em max_width sem nunca cortar palavras."""
    if not text:
        return []
    words = text.split()
    if not words:
        return []

    lines: List[str] = []
    current = words[0]

    def _split_long_word(word: str) -> List[str]:
        parts = []
        buf = ""
        for ch in word:
            if pdfmetrics.stringWidth(buf + ch, font_name, font_size) <= max_width or not buf:
                buf += ch
            else:
                parts.append(buf)
                buf = ch
        if buf:
            parts.append(buf)
        return parts

    # Caso a primeira palavra sozinha seja maior que a largura máxima
    if pdfmetrics.stringWidth(current, font_name, font_size) > max_width:
        split_first = _split_long_word(current)
        lines.extend(split_first[:-1])
        current = split_first[-1]

    for w in words[1:]:
        candidate = current + " " + w
        if pdfmetrics.stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            if pdfmetrics.stringWidth(w, font_name, font_size) > max_width:
                split_w = _split_long_word(w)
                lines.extend(split_w[:-1])
                current = split_w[-1]
            else:
                current = w

    if current:
        lines.append(current)
    return lines


def _should_use_two_cols(jobs: List[str]) -> bool:
    if not jobs or len(jobs) < 5:
        return False
    max_len = max((len(j) for j in jobs), default=0)
    return max_len <= 28


def _measure_cell_height(comp: Dict[str, Any], col_w: float, scale: float) -> float:
    """Calcula a altura necessária em pontos (pt) para renderizar uma célula sem cortar nada."""
    pad_x = 4.0 * scale
    pad_y = 3.5 * scale
    header_font_size = 6.8 * scale
    header_leading = header_font_size * 1.18
    badge_w = 13.0 * scale

    name_max_w = max(20.0, col_w - 2 * pad_x - badge_w - 3.0 * scale)
    name_lines = _wrap_text(str(comp.get("name", "")).upper(), "Helvetica-Bold", header_font_size, name_max_w)
    header_h = max(11.5 * scale, len(name_lines) * header_leading + 3.5 * scale)

    jobs = [str(j).upper() for j in (comp.get("jobs") or [])]
    job_font_size = 5.9 * scale
    job_leading = job_font_size * 1.20
    job_gap = 1.2 * scale

    if not jobs:
        jobs_h = job_leading
    elif _should_use_two_cols(jobs):
        sub_col_w = max(15.0, (col_w - 2 * pad_x - 4.0 * scale) / 2.0)
        mid = math.ceil(len(jobs) / 2.0)
        col1 = jobs[:mid]
        col2 = jobs[mid:]

        def _col_height(items: List[str]) -> float:
            h = 0.0
            for item in items:
                wrapped = _wrap_text(item, "Helvetica", job_font_size, sub_col_w)
                h += len(wrapped) * job_leading + job_gap
            return h

        jobs_h = max(_col_height(col1), _col_height(col2))
    else:
        full_w = max(20.0, col_w - 2 * pad_x)
        jobs_h = 0.0
        for item in jobs:
            wrapped = _wrap_text(item, "Helvetica", job_font_size, full_w)
            jobs_h += len(wrapped) * job_leading + job_gap

    return pad_y * 2 + header_h + 3.0 * scale + jobs_h


def _compute_rows_heights(companies_slice: List[Dict[str, Any]], col_w: float, scale: float) -> List[float]:
    row_heights: List[float] = []
    for r_start in range(0, len(companies_slice), COLS):
        row_Standard = companies_slice[r_start : r_start + COLS]
        max_h = max((_measure_cell_height(c, col_w, scale) for c in row_Standard), default=28.0 * scale)
        # Se for a última linha e tiver o QR Code embutido na linha, garante altura mínima para o QR Code
        is_last_row = (r_start + COLS) >= len(companies_slice)
        rem = len(companies_slice) % COLS
        free_cols = 0 if rem == 0 else (COLS - rem)
        if is_last_row and free_cols >= 2:
            max_h = max(max_h, 48.0 * scale)
        row_heights.append(max(max_h, 24.0 * scale))
    return row_heights


def _total_sheet_needed_height(companies_slice: List[Dict[str, Any]], col_w: float, scale: float) -> Tuple[float, List[float], bool]:
    header_h = 40.0 * scale
    row_heights = _compute_rows_heights(companies_slice, col_w, scale)
    rem = len(companies_slice) % COLS
    free_cols = 0 if rem == 0 else (COLS - rem)
    inline_qr = (free_cols >= 2 and len(companies_slice) > 0)
    footer_h = 0.0 if inline_qr else (48.0 * scale)
    total_h = header_h + sum(row_heights) + footer_h
    return total_h, row_heights, inline_qr


def _decode_custom_logo(logo_data_url: Optional[str]) -> Optional[ImageReader]:
    """Decodifica um logotipo raster (PNG/JPEG/WebP) caso o usuário tenha enviado um personalizado."""
    if not logo_data_url or not logo_data_url.startswith("data:image/"):
        return None
    if logo_data_url.startswith("data:image/svg"):
        return None
    try:
        header, b64_part = logo_data_url.split(",", 1)
        raw_bytes = base64.b64decode(b64_part)
        pil_img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        bg = Image.new("RGBA", pil_img.size, (220, 220, 220, 255))
        composed = Image.alpha_composite(bg, pil_img).convert("RGB")
        out = io.BytesIO()
        composed.save(out, format="PNG")
        out.seek(0)
        return ImageReader(out)
    except Exception:
        return None


def _draw_default_parana_logo(c: canvas.Canvas, x: float, y_bottom: float, h: float, scale: float) -> None:
    """Desenha o logotipo institucional vetorial PARANÁ - GOVERNO DO ESTADO no cabeçalho."""
    c.saveState()
    top = y_bottom + h
    c.setFillColor(colors.HexColor("#22252a"))
    c.setFont("Helvetica-Bold", 15.5 * scale)
    c.drawString(x + 4, top - 14.5 * scale, "PARANÁ")

    c.setFillColor(colors.HexColor("#374151"))
    c.setFont("Helvetica-Bold", 5.2 * scale)
    c.drawString(x + 4, top - 20.8 * scale, "GOVERNO DO ESTADO")

    c.setStrokeColor(colors.HexColor("#4b5563"))
    c.setLineWidth(0.7)
    c.line(x + 4, top - 22.8 * scale, x + 94 * scale, top - 22.8 * scale)

    c.setFont("Helvetica-Bold", 4.8 * scale)
    c.drawString(x + 4, top - 28.5 * scale, "SECRETARIA DO TRABALHO,")
    c.drawString(x + 4, top - 34.0 * scale, "QUALIFICAÇÃO E RENDA")

    # Escudo institucional estilizado à direita da inscrição
    bx = x + 98 * scale
    by = y_bottom + 4 * scale
    bw = 22 * scale
    bh = h - 8 * scale
    c.setFillColor(colors.HexColor("#22252a"))
    c.roundRect(bx, by, bw, bh, 3 * scale, stroke=0, fill=1)
    c.setStrokeColor(colors.white)
    c.setLineWidth(0.8)
    c.roundRect(bx + 2 * scale, by + 2 * scale, bw - 4 * scale, bh - 4 * scale, 2 * scale, stroke=1, fill=0)
    c.setFillColor(colors.HexColor("#dcdcdc"))
    c.circle(bx + bw / 2.0, by + bh * 0.62, 3.2 * scale, stroke=0, fill=1)
    c.restoreState()


def _draw_qr_block(
    c: canvas.Canvas,
    qr_reader: ImageReader,
    public_url: str,
    x_left: float,
    y_bottom: float,
    box_w: float,
    box_h: float,
    scale: float,
) -> None:
    """Desenha a chamada e o QR Code no canto inferior direito."""
    c.saveState()
    qr_size = min(box_h - 6.0 * scale, 44.0 * scale)
    qr_size = max(qr_size, 32.0 * scale)
    qr_x = x_left + box_w - qr_size - 8.0 * scale
    qr_y = y_bottom + (box_h - qr_size) / 2.0

    # Moldura branca do QR Code
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#9ca3af"))
    c.setLineWidth(0.5)
    c.rect(qr_x - 1.5, qr_y - 1.5, qr_size + 3, qr_size + 3, stroke=1, fill=1)
    c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size, preserveAspectRatio=True, mask="auto")

    # Seta indicativa
    arrow_x = qr_x - 16.0 * scale
    center_y = y_bottom + box_h / 2.0
    c.setFillColor(colors.HexColor("#111827"))
    c.setFont("Helvetica-Bold", 12.0 * scale)
    c.drawString(arrow_x, center_y - 4.0 * scale, "->")

    # Texto principal ao lado do QR Code
    text_right = arrow_x - 6.0 * scale
    cta_font = 8.5 * scale
    c.setFont("Helvetica-Bold", cta_font)
    line1 = "ESCANEIE O QR CODE E ACESSE O"
    line2 = "PAINEL DE VAGAS PELO CELULAR!"
    c.drawRightString(text_right, center_y + 2.5 * scale, line1)
    c.drawRightString(text_right, center_y - 7.0 * scale, line2)

    if public_url:
        c.setFont("Helvetica", max(4.8, 5.2 * scale))
        c.setFillColor(colors.HexColor("#4b5563"))
        c.drawRightString(text_right, center_y - 14.0 * scale, public_url)

    c.restoreState()


def _draw_sheet(
    c: canvas.Canvas,
    title: str,
    companies_slice: List[Dict[str, Any]],
    scale: float,
    row_heights: List[float],
    inline_qr: bool,
    qr_reader: ImageReader,
    public_url: str,
    custom_logo: Optional[ImageReader],
    header_style: str,
    page_idx: int,
    total_pages: int,
) -> None:
    x0 = MARGIN
    y0 = MARGIN
    top_y = y0 + SHEET_H

    # 1. Cabeçalho Institucional
    header_h = 40.0 * scale
    header_bottom = top_y - header_h
    c.setFillColor(colors.HexColor("#dcdcdc"))
    c.setStrokeColor(colors.HexColor("#4b5563"))
    c.setLineWidth(1.0)
    c.rect(x0, header_bottom, SHEET_W, header_h, stroke=1, fill=1)

    # Logotipo à esquerda
    logo_area_w = 135.0 * scale
    if custom_logo:
        c.drawImage(
            custom_logo,
            x0 + 6.0 * scale,
            header_bottom + 3.0 * scale,
            width=logo_area_w - 10.0 * scale,
            height=header_h - 6.0 * scale,
            preserveAspectRatio=True,
            anchor="w",
            mask="auto",
        )
    else:
        _draw_default_parana_logo(c, x0 + 4.0 * scale, header_bottom, header_h, scale)

    # Título centralizado
    title_max_w = SHEET_W - 2 * logo_area_w
    title_font = 13.5 * scale
    title_lines = _wrap_text((title or "MUTIRÃO EMPREGA | CASA DO TRABALHADOR").upper(), "Helvetica-Bold", title_font, title_max_w)
    if len(title_lines) > 2:
        title_font = 10.5 * scale
        title_lines = _wrap_text((title or "").upper(), "Helvetica-Bold", title_font, title_max_w)[:2]

    c.setFillColor(colors.HexColor("#090d16"))
    c.setFont("Helvetica-Bold", title_font)
    total_title_h = len(title_lines) * (title_font * 1.15)
    curr_ty = header_bottom + (header_h + total_title_h) / 2.0 - title_font * 0.88
    for tline in title_lines:
        c.drawCentredString(x0 + SHEET_W / 2.0, curr_ty, tline)
        curr_ty -= title_font * 1.15

    # Indicador de página quando houver múltiplas páginas
    if total_pages > 1:
        c.setFont("Helvetica-Bold", 6.5 * scale)
        c.setFillColor(colors.HexColor("#374151"))
        c.drawRightString(x0 + SHEET_W - 8.0 * scale, header_bottom + header_h / 2.0 - 2.5, f"PÁGINA {page_idx} DE {total_pages}")

    # 2. Grade de 7 Colunas
    col_w = SHEET_W / float(COLS)
    footer_h = 0.0 if inline_qr else (48.0 * scale)
    avail_grid_h = SHEET_H - header_h - footer_h

    # Distribui eventual espaço vertical restante proporcionalmente entre as linhas
    sum_rows = sum(row_heights)
    if sum_rows > 0 and avail_grid_h > sum_rows:
        extra_per_row = (avail_grid_h - sum_rows) / float(len(row_heights))
        stretched_heights = [rh + extra_per_row for rh in row_heights]
    else:
        stretched_heights = row_heights

    curr_row_top = header_bottom
    num_rows = len(stretched_heights)

    for r_idx in range(num_rows):
        rh = stretched_heights[r_idx]
        row_bottom = curr_row_top - rh
        row_slice = companies_slice[r_idx * COLS : (r_idx + 1) * COLS]

        for c_idx, comp in enumerate(row_slice):
            cell_x = x0 + c_idx * col_w
            _draw_company_cell(c, comp, cell_x, row_bottom, col_w, rh, scale, header_style)

        # Se for a última linha e tiver QR Code inline nas colunas restantes
        if r_idx == num_rows - 1 and inline_qr:
            used_cols = len(row_slice)
            free_cols = COLS - used_cols
            qr_cell_x = x0 + used_cols * col_w
            qr_cell_w = free_cols * col_w
            c.setStrokeColor(colors.HexColor("#9ca3af"))
            c.setLineWidth(0.6)
            c.rect(qr_cell_x, row_bottom, qr_cell_w, rh, stroke=1, fill=0)
            _draw_qr_block(c, qr_reader, public_url, qr_cell_x, row_bottom, qr_cell_w, rh, scale)

        curr_row_top = row_bottom

    # 3. Rodapé dedicado de QR Code (quando a última linha tem < 2 colunas livres)
    if not inline_qr:
        footer_bottom = y0
        c.setStrokeColor(colors.HexColor("#4b5563"))
        c.setLineWidth(0.8)
        c.rect(x0, footer_bottom, SHEET_W, footer_h, stroke=1, fill=0)
        _draw_qr_block(c, qr_reader, public_url, x0, footer_bottom, SHEET_W, footer_h, scale)

    # Moldura externa da folha
    c.setStrokeColor(colors.HexColor("#4b5563"))
    c.setLineWidth(1.2)
    c.rect(x0, y0, SHEET_W, SHEET_H, stroke=1, fill=0)


def _draw_company_cell(
    c: canvas.Canvas,
    comp: Dict[str, Any],
    cell_x: float,
    cell_y: float,
    col_w: float,
    cell_h: float,
    scale: float,
    header_style: str,
) -> None:
    c.saveState()
    # Borda da célula
    c.setStrokeColor(colors.HexColor("#9ca3af"))
    c.setLineWidth(0.6)
    c.rect(cell_x, cell_y, col_w, cell_h, stroke=1, fill=0)

    pad_x = 3.5 * scale
    pad_y = 3.0 * scale
    top_y = cell_y + cell_h - pad_y

    header_font_size = 6.8 * scale
    header_leading = header_font_size * 1.16
    badge_w = 13.0 * scale
    badge_h = 9.5 * scale

    name_max_w = max(20.0, col_w - 2 * pad_x - badge_w - 3.0 * scale)
    name_lines = _wrap_text(str(comp.get("name", "")).upper(), "Helvetica-Bold", header_font_size, name_max_w)
    header_box_h = max(11.5 * scale, len(name_lines) * header_leading + 3.2 * scale)

    is_dark = (header_style != "classic")

    if is_dark:
        # Faixa escura de identificação com texto branco
        strip_x = cell_x + 1.2
        strip_w = col_w - 2.4
        strip_y = cell_y + cell_h - header_box_h - 1.2
        c.setFillColor(colors.HexColor("#18202c"))
        c.rect(strip_x, strip_y, strip_w, header_box_h, stroke=0, fill=1)

        # Selo branco com número da empresa
        bx = strip_x + 2.2 * scale
        by = strip_y + header_box_h - badge_h - 1.4 * scale
        c.setFillColor(colors.white)
        c.roundRect(bx, by, badge_w, badge_h, 1.5, stroke=0, fill=1)

        c.setFillColor(colors.HexColor("#111827"))
        c.setFont("Helvetica-Bold", 6.2 * scale)
        c.drawCentredString(bx + badge_w / 2.0, by + 2.1 * scale, str(comp.get("number", "")))

        # Nome da empresa em branco e negrito
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", header_font_size)
        ny = strip_y + header_box_h - header_font_size - 1.6 * scale
        for nline in name_lines:
            c.drawString(bx + badge_w + 2.8 * scale, ny, nline)
            ny -= header_leading

        jobs_top_y = strip_y - 3.0 * scale
    else:
        # Estilo clássico: selo escuro + texto escuro
        bx = cell_x + pad_x
        by = top_y - badge_h
        c.setFillColor(colors.HexColor("#18181b"))
        c.roundRect(bx, by, badge_w, badge_h, 1.5, stroke=0, fill=1)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 6.2 * scale)
        c.drawCentredString(bx + badge_w / 2.0, by + 2.1 * scale, str(comp.get("number", "")))

        c.setFillColor(colors.HexColor("#111827"))
        c.setFont("Helvetica-Bold", header_font_size)
        ny = top_y - header_font_size * 0.92
        for nline in name_lines:
            c.drawString(bx + badge_w + 2.8 * scale, ny, nline)
            ny -= header_leading

        jobs_top_y = cell_y + cell_h - pad_y - header_box_h - 2.0 * scale

    # Lista de vagas da empresa
    jobs = [str(j).upper() for j in (comp.get("jobs") or [])]
    job_font_size = 5.9 * scale
    job_leading = job_font_size * 1.18
    job_gap = 1.1 * scale

    c.setFillColor(colors.HexColor("#1f2937"))
    c.setFont("Helvetica", job_font_size)

    if _should_use_two_cols(jobs):
        sub_col_w = max(15.0, (col_w - 2 * pad_x - 4.0 * scale) / 2.0)
        mid = math.ceil(len(jobs) / 2.0)
        col1 = jobs[:mid]
        col2 = jobs[mid:]

        for col_idx, col_items in enumerate((col1, col2)):
            cx = cell_x + pad_x + col_idx * (sub_col_w + 4.0 * scale)
            cy = jobs_top_y - job_font_size * 0.85
            for item in col_items:
                wlines = _wrap_text(item, "Helvetica", job_font_size, sub_col_w)
                for wl in wlines:
                    if cy >= cell_y + 1.5:
                        c.drawString(cx, cy, wl)
                    cy -= job_leading
                cy -= job_gap
    else:
        full_w = max(20.0, col_w - 2 * pad_x)
        cx = cell_x + pad_x
        cy = jobs_top_y - job_font_size * 0.85
        for item in jobs:
            wlines = _wrap_text(item, "Helvetica", job_font_size, full_w)
            for wl in wlines:
                if cy >= cell_y + 1.5:
                    c.drawString(cx, cy, wl)
                cy -= job_leading
            cy -= job_gap

    c.restoreState()


def generate_panel_pdf_sync(
    title: str,
    companies: List[Dict[str, Any]],
    public_url: str,
    logo_data_url: Optional[str] = None,
    header_style: str = "dark",
) -> bytes:
    """Gera o PDF A4 Paisagem completo em memória."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    c.setTitle(title or "Painel de Vagas — Agência do Trabalhador de Curitiba")

    # Prepara imagem do QR Code
    qr_data_url = generate_qr_png_data_url(public_url, box_size=10, border=1)
    _, qr_b64 = qr_data_url.split(",", 1)
    qr_reader = ImageReader(io.BytesIO(base64.b64decode(qr_b64)))

    custom_logo = _decode_custom_logo(logo_data_url)
    col_w = SHEET_W / float(COLS)

    # 1. Tenta manter todas as empresas em uma única página A4 Paisagem dentro de limites legíveis
    candidate_scales = [1.28, 1.18, 1.08, 1.00, 0.94, 0.88, 0.82, 0.77, 0.72, 0.68, 0.64]
    fitted_single = False
    chosen_scale = 0.80
    chosen_rows: List[float] = []
    chosen_inline_qr = False

    if len(companies) <= 70:
        for sc in candidate_scales:
            total_h, r_heights, in_qr = _total_sheet_needed_height(companies, col_w, sc)
            if total_h <= SHEET_H:
                fitted_single = True
                chosen_scale = sc
                chosen_rows = r_heights
                chosen_inline_qr = in_qr
                break

    if fitted_single:
        _draw_sheet(
            c=c,
            title=title,
            companies_slice=companies,
            scale=chosen_scale,
            row_heights=chosen_rows,
            inline_qr=chosen_inline_qr,
            qr_reader=qr_reader,
            public_url=public_url,
            custom_logo=custom_logo,
            header_style=header_style,
            page_idx=1,
            total_pages=1,
        )
        c.showPage()
    else:
        # 2. Paginação automática inteligente quando não cabe em 1 única página
        multi_scale = 0.84
        slices: List[Tuple[List[Dict[str, Any]], List[float], bool]] = []
        cursor = 0
        while cursor < len(companies):
            best_slice = companies[cursor : cursor + COLS]
            _, best_rh, best_in_qr = _total_sheet_needed_height(best_slice, col_w, multi_scale)
            for candidate_rows_count in range(9, 0, -1):
                slice_cand = companies[cursor : cursor + candidate_rows_count * COLS]
                tot_h, rh_cand, in_qr_cand = _total_sheet_needed_height(slice_cand, col_w, multi_scale)
                if tot_h <= SHEET_H:
                    best_slice = slice_cand
                    best_rh = rh_cand
                    best_in_qr = in_qr_cand
                    break
            slices.append((best_slice, best_rh, best_in_qr))
            cursor += len(best_slice)

        for idx, (comp_slice, rh_list, in_qr) in enumerate(slices, start=1):
            _draw_sheet(
                c=c,
                title=title,
                companies_slice=comp_slice,
                scale=multi_scale,
                row_heights=rh_list,
                inline_qr=in_qr,
                qr_reader=qr_reader,
                public_url=public_url,
                custom_logo=custom_logo,
                header_style=header_style,
                page_idx=idx,
                total_pages=len(slices),
            )
            c.showPage()

    c.save()
    return buffer.getvalue()


async def generate_panel_pdf(
    title: str,
    companies: List[Dict[str, Any]],
    public_url: str,
    logo_data_url: Optional[str] = None,
    header_style: str = "dark",
) -> bytes:
    """Wrapper assíncrono para geração de PDF."""
    return generate_panel_pdf_sync(
        title=title,
        companies=companies,
        public_url=public_url,
        logo_data_url=logo_data_url,
        header_style=header_style,
    )
