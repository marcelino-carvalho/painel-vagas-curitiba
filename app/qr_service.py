"""
Serviço de geração de QR Codes em alta resolução (PNG Base64 e SVG).
"""

import base64
import io
import qrcode
import qrcode.image.svg


def generate_qr_png_data_url(url: str, box_size: int = 10, border: int = 1) -> str:
    """
    Gera um QR Code em formato PNG codificado em Data URL (base64)
    pronto para incorporação direta em HTML e PDF.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"
