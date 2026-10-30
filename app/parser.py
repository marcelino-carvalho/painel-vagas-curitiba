"""
Módulo de interpretação (parsing) do texto de empresas e vagas.
Segue rigorosamente as regras definidas na especificação da Agência do Trabalhador de Curitiba.
"""

from typing import List, Dict, Any
import re


def parse_vagas_text(raw_text: str) -> Dict[str, Any]:
    """
    Interpreta o texto bruto inserido pelo funcionário e retorna a lista estruturada
    de empresas e vagas, além dos contadores totais.

    Regras aplicadas:
    - Primeira linha de cada bloco = nome da empresa.
    - Linhas seguintes do bloco = vagas oferecidas por aquela empresa.
    - Uma ou mais linhas em branco consecutivas indicam o início de uma nova empresa.
    - Ignora espaços desnecessários no início e no final de cada linha.
    - Ignora linhas vazias no início, meio (múltiplas consecutivas) e fim do texto.
    - Preserva acentos e caracteres especiais.
    - Não descarta informações digitadas (mesmo empresa ainda sem vagas digitadas).
    """
    if not raw_text or not raw_text.strip():
        return {
            "companies": [],
            "total_companies": 0,
            "total_jobs": 0,
        }

    # Normaliza quebras de linha Windows/Mac/Unix
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")

    blocks: List[List[str]] = []
    current_block: List[str] = []

    for line in lines:
        cleaned = line.strip()
        # Remove múltiplos espaços internos excessivos mantendo todo o conteúdo e acentuação
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        if cleaned == "":
            if current_block:
                blocks.append(current_block)
                current_block = []
        else:
            current_block.append(cleaned)

    if current_block:
        blocks.append(current_block)

    companies: List[Dict[str, Any]] = []
    total_jobs = 0

    for idx, block in enumerate(blocks, start=1):
        company_name = block[0]
        jobs = block[1:] if len(block) > 1 else []
        total_jobs += len(jobs)
        companies.append({
            "number": idx,
            "name": company_name,
            "jobs": jobs,
            "job_count": len(jobs),
        })

    return {
        "companies": companies,
        "total_companies": len(companies),
        "total_jobs": total_jobs,
    }


SAMPLE_MUTIRAO_TEXT = """AÇÃO SOCIAL DO PARANA
AUX DE PRODUÇÃO (COZINHA)
NUTRICIONISTA
ASSISTENTE ADMINISTRATIVO
CUIDADOR DE IDOSOS

ADECCO
AUXILIAR DE LOGISTICA

ADM PARANÁ
SERVENTE DE LIMPEZA

ALIANÇA SUL
OPERADOR DE TELEMARKETING ATIVO E RECEPTIVO

ANGELONI
ATENDENTE DE PADARIA
AUXILIAR DE LIMPEZA
REPOSITOR DE MERCADORIAS
VENDEDORA DE ELETRO
PROMOTOR DE VENDAS - CARTÕES
ATENDENTE DE FARMÁCIA

BELARINA ALIMENTOS
EMBALADOR A MÃO

BURGUER KING
ATENDENTE DE RESTAURANTE

CACAU SHOW
OPERADOR DE LOJA

CALL FARMA
AUXILIAR DE ESTOQUE
ATENDENTE DE FARMACIA
ZELADOR

CAPRIGEM
ANALISTA FISCAL

CIA VERDE
MOTORISTA

CLINICA ANJOS DA GUARDA HOME CAR
CUIDADOR DE IDOSOS

CLUBE CURITIBANO
AUXILIAR DE LIMPEZA

CONCENTRIX
OPERADOR DE TELEMARKETING

CONDOR
OP DE CAIXA
REP DE MERCADORIAS
FISCAL DE LOJA
AT DE PADARIA
BALC DE AÇOUGUE
ZELADOR
AUX DE COZINHA
AUX DE LOGISTICA
AJUDANTE DE CARGA E DESCARGA

CONECTON CONTACT CENTER
CONSULTOR DE VENDAS

CONNECTMAIS - RH PRIMEIRA OPÇÃO
VENDEDOR EXTERNO

DBM CONTACT
OPERADOR DE TELEMARKETING

DESTRO MACROATACADO
AUXILIAR DE LOGISTICA
MOTORISTA DE CAMINHÃO

DINA PIZZA
ATENDENTE DE LANCHONETE

ENGELMIG
LEITURISTA
LEITURISTA DE MOTOCICLETA

EXPRESSO SÃO MIGUEL
AUXILIAR DE CARGA E DESCARGA

FESTVAL
AUXILIAR DE PRODUÇÃO
AUXILIAR DE LOGISTICA
AUXILIAR DE COZINHA

FFA INFRAESTRUTURA
REPARADOR DE LINHAS DE TELECOMUNICAÇÃO

GELOPAR
OPERADOR MULTIFUNCIONAL

GERAÇÃO DE SAÚDE
CUIDADOR DE IDOSO

GRSA
AJUDANTE DE COZINHA
AUXILIAR DE COZINHA

GRUPO OPUS
AUXILIAR DE LINHA DE PRODUÇÃO

HIPERZOO
VENDEDOR INTERNO
OPERADOR DE CAIXA
REPOSITOR DE MERCADORIAS

HONDA MOTOCAR
VENDEDOR EXTERNO

ILUVIA ENGENHARIA
SERVENTE DE OBRAS
CARPINTEIRO/ARMADOR

IMEDIATA RH
AUXILIAR DE LOGISTICA
AUXILIAR DE PRODUÇÃO

ITALO
OPERADOR DE CAIXA
ATENDENTE DE PADARIA

KHARINA
OPERADOR DE CAIXA
ATENDENTE DE PADARIA

LEADEC
LIMPADOR TÉCNICO
MECÂNICO DE MANUTENÇÃO DE MÁQUINAS

LIDERANÇA
AUXILIAR DE LIMPEZA

LOJAS COLOMBO
MONTADOR DE CARGA
OPERADOR LOGISTICO
OPERADOR DE EMPILHADEIRA
MOTORISTA DE CAMINHAO
AUXILIAR ADMINISTRATIVO
ASSISTENTE ADMINISTRATIVO

MARQUESPAM
AUX DE PRODUÇÃO

MERCADO BELLA VILLA
OP DE LOJA
ENCARREGADO DE LOJA
AUXILIAR DE PADARIA
OP CAIXA
REPOSITOR
AÇOUGUEIRO
AUX DE LIMPEZA

MUFFATO
OPERADOR DE CAIXA
REPOSITOR DE MERCADORIAS
AÇOUGUEIRO
FISCAL DE PREV DE PERDAS
ATENDENTE BALCONISTA
AJUDANTE DE AÇOUGUE

NISSEI
OPERADOR DE CAIXA
ATENDENTE DE FARMÁCIA
FARMACÊUTICO

ORBENK
AUXILIAR DE LIMPEZA

PLASTILIT
AUXILIAR DE PRODUÇÃO

PLATINOX
ALMOXARIFE

PONTUAL
AUXILIAR DE LIMPEZA
SERVENTE DE LIMPEZA
LIMPADOR DE VIDROS
JARDINEIRO

POSIGRAF
AUXILIAR DE LOGÍSTICA

RAC ENGENHARIA
PEDREIRO
SERVENTE

RECANTO GAUCHO
AUXILIAR DE SERVIÇOS DE ALIMENTAÇÃO

RIACHUELO
OPERADOR DE CAIXA

RISOTOLANDIA
AUXILIAR DE COZINHA
COZINHEIRO

ROMPLAS
AUXILIAR DE PRODUÇÃO

RULIWI
AUXILIAR DE COZINHA

SENFF
VENDEDOR EXTERNO

SERV LAR
FAXINEIRO

SINGULAR
AUXILIAR DE LIMPEZA
PORTEIRO
AUXILIAR DE MANUTENÇÃO PREDIAL

SOFTMARKETING
OPERADOR DE TELEMARKETING

TAHTO
OPERADOR DE TELEMARKETING

TERCEIRIZE MAIS
AUXILIAR DE LIMPEZA HOSPITALAR
AUXILIAR DE LIMPEZA
ENCARREGADO DE JARDINAGEM

TRC TABORDA
OPERADOR DE TELEMARKETING

UNIDAS
ASSISTENTE ADMINISTRATIVO

UNILEHU
AUXILIAR DE LOJA

VEPER
PORTEIRO
SERVENTE DE LIMPEZA
MANUTENÇÃO PREDIAL

VERSANI & SANDRINI
FAXINEIRO

VERTICE STRUTURAL
ARQUITETO
DESIGNER DE AMBIENTES
SECRETARIA
VENDEDOR

VUELO PHARMA
AUX DE PRODUÇÃO"""
