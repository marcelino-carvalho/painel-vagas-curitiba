# 🏢 Sistema de Criação de Painel de Vagas — Agência do Trabalhador de Curitiba

> **Solução Full Stack de alto impacto social para automação, diagramação institucional em PDF A4 e publicação digital em tempo real com QR Code para mutirões de emprego.**

---

## 🎯 Sobre o Projeto

Nos mutirões de emprego da **Agência do Trabalhador de Curitiba (Secretaria do Trabalho, Qualificação e Renda / Governo do Paraná)**, dezenas de empresas ofertam centenas de vagas simultaneamente. A consolidação dessas informações costumava ser manual e demorada.

Este sistema foi desenvolvido com foco em **experiência do usuário (UX), produtividade e robustez**, permitindo que um operador apenas cole a lista bruta de empresas e vagas em um **campo único de texto**. Em tempo real, a plataforma:

1. **Interpreta e estrutura os dados automaticamente** (identificando empresas, cargos, limpando formatações e preservando acentuação).
2. **Gera uma pré-visualização instantânea em grade proporcional (7 colunas)** conforme a identidade visual oficial.
3. **Exporta um documento PDF em formato A4 Paisagem** de alta definição pronto para impressão, com nomeação inteligente idêntica ao título do evento.
4. **Publica um mural digital responsivo na web** com URL exclusiva e gera um **QR Code funcional no próprio PDF**, permitindo que milhares de candidatos consultem as vagas na tela do smartphone sem filas ou lentidão.

---

## ✨ Principais Funcionalidades

- **Parser Inteligente de Entrada Única:**
  - 1ª linha do bloco = Nome da Empresa.
  - Linhas subsequentes = Cargos/Vagas.
  - Linha em branco = Próxima empresa.
  - Tratamento resiliente de espaços em branco, quebras extras e caracteres especiais.
- **Diagramação e Exportação PDF Ultra-Leve:**
  - Desenvolvido com **ReportLab** nativo em Python, eliminando dependências pesadas de navegadores headless.
  - Consumo mínimo de memória (< 15 MB) e geração instantânea (< 100ms).
  - Cálculo automático de escala tipográfica e subcolunamento para comportar de 1 a 65+ empresas em uma única folha A4 Paisagem, com paginação fluida caso o volume exceda os limites legíveis.
- **Personalização de Identidade Visual:**
  - Cabeçalho institucional com o Brasão do Paraná e Logo da Secretaria do Trabalho.
  - Opção para substituir a logo esquerda e suporte a **logotipo secundário à direita (opcional)** com pré-visualização imediata.
  - Destaque em faixa escura institucional ou modo clássico.
- **Mural Público Mobile-First:**
  - Interface limpa e acessível para qualquer dispositivo móvel.
  - Busca e filtro dinâmico por empresa ou cargo em tempo real.
  - Sem necessidade de login ou cadastro para os candidatos.
- **Modo Anti-Hibernação (Dia do Mutirão):**
  - Chave inteligente desenvolvida especificamente para hospedagens serverless/free-tier (como o Render).
  - Quando ativada pelo operador no dia do evento, mantém o serviço aquecido via pings periódicos controlados, garantindo carregamento instantâneo do QR Code sem atrasos de *cold start*. Ao término do evento, basta desativar para economizar recursos.
- **Túnel Público Automático & Suporte Cloud:**
  - Em desenvolvimento local, provisiona túnel seguro HTTPS (Cloudflare Tunnel) para que os QR Codes gerados no computador já funcionem de verdade no 4G/5G de qualquer celular.
  - Em produção (Render, Railway, Cloud Run), autodetecta o domínio público HTTPS oficial.

---

## 🛠️ Tecnologias Utilizadas

- **Back-end:** Python 3, FastAPI, Uvicorn, Pydantic, SQLite3 (Persistência com slugs permanentes).
- **Geração de Documentos:** ReportLab (PDF vetorial A4 Paisagem), QRCode, Pillow.
- **Front-end:** HTML5 semântico, CSS3 moderno (Grid, Flexbox, Variáveis CSS, Glassmorphism suave), JavaScript Vanilla (reatividade instantânea sem frameworks pesados).
- **DevOps & Qualidade:** Docker, Cloudflare Quick Tunnels, Pytest, PyPDF, Playwright (Testes E2E de responsividade).

---

## 🏛️ Arquitetura do Repositório

```text
├── app/
│   ├── database.py       # Persistência SQLite de painéis, slugs únicos e modo mutirão
│   ├── default_logo.py   # Gerenciamento de identidades visuais padrão em alta resolução
│   ├── main.py           # Rotas da API FastAPI, injeção de templates e keep-alive worker
│   ├── parser.py         # Motor de processamento léxico e normalização textual
│   ├── pdf_service.py    # Motor ReportLab de diagramação vetorial em A4 Paisagem
│   ├── qr_service.py     # Geração de QR Codes otimizados em Base64
│   └── tunnel.py         # Resolução dinâmica de domínio público (Cloud/Cloudflare)
├── data/                 # Banco de dados local SQLite
├── static/
│   ├── css/admin.css     # Estilos da interface administrativa e preview
│   ├── img/              # Imagens e brasões institucionais
│   └── js/               # Reatividade, parser client-side e gerenciador de estado
├── templates/
│   ├── index.html        # Painel de controle e estúdio de criação
│   └── public_panel.html # Página pública mobile para candidatos
├── tests/
│   └── test_acceptance.py # Bateria de testes automatizados dos critérios de aceitação
├── Dockerfile            # Containerização otimizada para deploy em nuvem
├── requirements.txt      # Dependências enxutas do projeto
└── iniciar_sistema.bat   # Script de inicialização em 1 clique para Windows
```

---

## 🚀 Como Executar Localmente

### Pré-requisitos
- Python 3.10 ou superior instalado.

### 1. Clonar e Instalar Dependências
```bash
git clone https://github.com/marcelino-carvalho/painel-vagas-curitiba.git
cd painel-vagas-curitiba
pip install -r requirements.txt
```

### 2. Iniciar a Aplicação
No Windows, basta dar dois cliques em **`iniciar_sistema.bat`** ou rodar:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- Acesse o painel administrativo em: `http://localhost:8000`

---

## 🧪 Qualidade de Código e Testes Automatizados

O projeto conta com uma suíte de testes de ponta a ponta cobrindo os cenários de negócio (tratamento de espaçamentos, blocos extensos, integridade de slugs, consistência dos dados extraídos do PDF e responsividade mobile):

```bash
pytest tests/test_acceptance.py -v
```

---

## 👨‍💻 Autor

Desenvolvido por **Marcelino Carvalho**.  
Projeto voltado à modernização de processos públicos e inclusão produtiva.
