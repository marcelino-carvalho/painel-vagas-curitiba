"""
Suíte de Testes Automatizados dos 10 Critérios de Aceitação (Seção 9 da Especificação)
Inclui testes unitários do parser, testes de API, verificação de PDF (pypdf) e testes de responsividade/E2E.
"""

import io
import re
import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

from app.main import app
from app.parser import SAMPLE_MUTIRAO_TEXT, parse_vagas_text
from app.tunnel import is_local_or_private_host


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_criterio_1_uma_empresa_cinco_vagas():
    """1. Inserir uma empresa com cinco vagas e verificar se todas aparecem na mesma célula."""
    raw = (
        "SUPERMERCADO CURITIBA\n"
        "Operador de Caixa\n"
        "Repositor de Mercadorias\n"
        "Atendente de Padaria\n"
        "Açougueiro\n"
        "Auxiliar de Logística"
    )
    res = parse_vagas_text(raw)
    assert res["total_companies"] == 1
    assert res["total_jobs"] == 5
    comp = res["companies"][0]
    assert comp["number"] == 1
    assert comp["name"] == "SUPERMERCADO CURITIBA"
    assert len(comp["jobs"]) == 5
    assert "Açougueiro" in comp["jobs"]


def test_criterio_2_tres_empresas_linhas_em_branco_extras():
    """2. Inserir três empresas separadas por linhas em branco (incluindo múltiplas e finais) e verificar identificação."""
    raw = (
        "\n\n  EMPRESA ALFA  \n"
        "  Auxiliar Administrativo \n"
        "Operador de Caixa\n\n\n\n"
        "EMPRESA BETA\n"
        "Auxiliar de Produção\n\n"
        "EMPRESA GAMA\n"
        "Motorista\n"
        "Analista Fiscal\n\n\n   \n"
    )
    res = parse_vagas_text(raw)
    assert res["total_companies"] == 3
    assert res["total_jobs"] == 5
    assert [c["name"] for c in res["companies"]] == [
        "EMPRESA ALFA",
        "EMPRESA BETA",
        "EMPRESA GAMA",
    ]


def test_criterio_3_textos_extensos_e_caracteres_especiais():
    """3. Inserir nomes de empresas e vagas com textos extensos e acentuação complexa."""
    long_company = "COOPERATIVA PARANAENSE DE LOGÍSTICA INTEGRADA & MANUTENÇÃO INDUSTRIAL S/A (UNIDADE CIC)"
    long_job = "TÉCNICO ESPECIALISTA EM MANUTENÇÃO ELETROMECÂNICA DE EQUIPAMENTOS PESADOS (1º, 2º E 3º TURNOS)"
    raw = f"{long_company}\n{long_job}"
    res = parse_vagas_text(raw)
    assert res["total_companies"] == 1
    assert res["companies"][0]["name"] == long_company
    assert res["companies"][0]["jobs"][0] == long_job


def test_criterio_4_mais_de_50_empresas_modelo_referencia():
    """4. Inserir mais de 50 empresas (65 empresas do modelo de referência) e verificar organização."""
    res = parse_vagas_text(SAMPLE_MUTIRAO_TEXT)
    assert res["total_companies"] == 65
    assert res["total_jobs"] > 120
    assert res["companies"][0]["name"] == "AÇÃO SOCIAL DO PARANA"
    assert res["companies"][64]["name"] == "VUELO PHARMA"
    assert res["companies"][64]["number"] == 65


def test_criterio_5_6_7_8_9_10_fluxo_completo(client: TestClient):
    """
    Testa os critérios 5, 6, 7, 8, 9 e 10 integrados:
    - Publica painel com 65 empresas e título personalizado.
    - Verifica que o endereço público NÃO é localhost/IP privado.
    - Verifica que a página pública responde com o título e todas as 65 empresas.
    - Atualiza o painel já publicado (novo título e vaga editada) e confirma que o endereço público permanece IDÊNTICO.
    - Exporta o PDF e verifica com pypdf que todas as informações e o texto do QR Code estão presentes.
    - Abre a página pública em viewport de celular (375x812) e confirma responsividade sem overflow horizontal.
    """
    # Publicação inicial
    pub_res = client.post(
        "/api/panels",
        json={
            "title": "MUTIRÃO EMPREGA + PINHEIRINHO | CASA DO TRABALHADOR",
            "raw_text": SAMPLE_MUTIRAO_TEXT,
            "header_style": "dark",
        },
    )
    assert pub_res.status_code == 200
    data1 = pub_res.json()
    slug1 = data1["slug"]
    public_url1 = data1["public_url"]

    # Critério 8: O endereço público não pode ser localhost nem IP privado
    host_only = re.sub(r"^https?://", "", public_url1).split("/")[0]
    assert not is_local_or_private_host(host_only), f"URL gerada é privada/local: {public_url1}"
    assert public_url1.startswith("https://")
    assert data1["qr_data_url"].startswith("data:image/png;base64,")

    # Critério 6 e 9: Editar uma vaga e o título num painel já publicado e republicar mantém o MESMO endereço público
    updated_text = SAMPLE_MUTIRAO_TEXT + "\nDESENVOLVEDOR DE SISTEMAS SENIOR"
    new_title = "MUTIRÃO EMPREGA + BOQUEIRÃO ATUALIZADO | CASA DO TRABALHADOR"
    pub_res2 = client.post(
        "/api/panels",
        json={
            "title": new_title,
            "raw_text": updated_text,
            "slug": slug1,
            "header_style": "dark",
        },
    )
    assert pub_res2.status_code == 200
    data2 = pub_res2.json()
    assert data2["slug"] == slug1
    assert data2["public_url"] == public_url1

    # Verifica que a página pública exibe o título atualizado e a nova vaga
    pub_html_res = client.get(f"/p/{slug1}")
    assert pub_html_res.status_code == 200
    html_text = pub_html_res.text
    assert new_title in html_text
    assert "DESENVOLVEDOR DE SISTEMAS SENIOR" in html_text
    assert "VUELO PHARMA" in html_text

    # Critério 10: Abrir a página pública em um celular (375x812) e verificar a responsividade
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        mobile_page = browser.new_page(viewport={"width": 375, "height": 812, "is_mobile": True})
        mobile_page.set_content(html_text, wait_until="load")
        overflow = mobile_page.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        assert not overflow, "A página pública não deve ter rolagem horizontal no celular"
        cards_count = mobile_page.locator(".company-card").count()
        assert cards_count == 65
        browser.close()

    # Critério 5 e 7: Exportar PDF e verificar presença de todas as informações
    pdf_res = client.get(f"/api/panels/{slug1}/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"

    reader = PdfReader(io.BytesIO(pdf_res.content))
    assert len(reader.pages) == 1  # 65 empresas cabem em 1 página A4 Paisagem
    extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "MUTIRÃO EMPREGA + BOQUEIRÃO ATUALIZADO" in extracted_text
    assert "AÇÃO SOCIAL DO PARANA" in extracted_text
    assert "VUELO PHARMA" in extracted_text
    assert "DESENVOLVEDOR DE SISTEMAS SENIOR" in extracted_text
    assert "ESCANEIE O QR CODE E ACESSE O PAINEL DE VAGAS PELO CELULAR!" in extracted_text
