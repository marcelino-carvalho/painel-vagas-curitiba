"""
Logotipo institucional padrão em formato SVG vetorial (Data URL)
para o cabeçalho do painel da Agência do Trabalhador / Secretaria do Trabalho.
O usuário pode substituir este logotipo por qualquer imagem personalizada na interface.
"""

import base64

DEFAULT_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 340 88" width="340" height="88">
  <rect width="340" height="88" fill="none"/>
  <!-- Texto Institucional -->
  <text x="6" y="34" font-family="Arial Black, Impact, Inter, sans-serif" font-weight="900" font-size="33" letter-spacing="1.2" fill="#2b2d30">PARANÁ</text>
  <text x="8" y="48" font-family="Arial, Inter, sans-serif" font-weight="700" font-size="10.2" letter-spacing="2.4" fill="#3f4246">GOVERNO DO ESTADO</text>
  <line x1="8" y1="53" x2="188" y2="53" stroke="#4a4d52" stroke-width="1.3"/>
  <text x="8" y="66" font-family="Arial, Inter, sans-serif" font-weight="700" font-size="9.5" letter-spacing="0.6" fill="#3f4246">SECRETARIA DO TRABALHO,</text>
  <text x="8" y="78" font-family="Arial, Inter, sans-serif" font-weight="700" font-size="9.5" letter-spacing="0.6" fill="#3f4246">QUALIFICAÇÃO E RENDA</text>

  <!-- Brasão Estilizado Institucional -->
  <g transform="translate(200, 6)">
    <!-- Ramos laterais -->
    <path d="M12,62 C5,48 5,28 14,14 C10,28 11,46 18,60 Z" fill="#3f4246"/>
    <path d="M64,62 C71,48 71,28 62,14 C66,28 65,46 58,60 Z" fill="#3f4246"/>
    <!-- Escudo -->
    <path d="M18,14 L58,14 L58,40 C58,56 38,68 38,68 C38,68 18,56 18,40 Z" fill="#2b2d30" stroke="#ffffff" stroke-width="1.5"/>
    <path d="M22,18 L54,18 L54,39 C54,52 38,62 38,62 C38,62 22,52 22,39 Z" fill="#dcdcdc"/>
    <!-- Sol e montanhas no escudo -->
    <circle cx="38" cy="29" r="6" fill="#2b2d30"/>
    <path d="M23,44 L33,35 L42,42 L48,37 L53,44 L53,48 L23,48 Z" fill="#3f4246"/>
    <!-- Falcão Harpia / Topo -->
    <path d="M28,12 C33,6 43,6 48,12 L42,14 L34,14 Z" fill="#2b2d30"/>
    <!-- Faixa inferior -->
    <path d="M12,69 Q38,76 64,69 L62,74 Q38,81 14,74 Z" fill="#2b2d30"/>
  </g>
</svg>"""

DEFAULT_LOGO_DATA_URL = (
    "data:image/svg+xml;base64,"
    + base64.b64encode(DEFAULT_LOGO_SVG.encode("utf-8")).decode("ascii")
)
