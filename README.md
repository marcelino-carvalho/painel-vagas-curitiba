# Sistema de Criação de Painel de Vagas — Agência do Trabalhador de Curitiba

Aplicação web completa para a criação automatizada, publicação na internet (com QR Code funcional) e exportação em PDF (A4 Paisagem) de painéis de vagas de emprego destinados aos mutirões da **Agência do Trabalhador de Curitiba / Casa do Trabalhador**.

---

## 1. Arquitetura do Sistema

O projeto foi estruturado separando claramente a interface, o interpretador de dados, o armazenamento persistente, a publicação pública e o motor de geração de PDF:

- **`app/parser.py` & `static/js/parser.js`**: Motor de interpretação automática do texto bruto digitado ou colado no campo único (primeira linha do bloco = empresa; linhas seguintes = vagas; uma ou mais linhas em branco = separador de nova empresa).
- **`app/database.py`**: Persistência em banco SQLite (`data/paineis.db`), garantindo que cada painel publicado receba um endereço exclusivo (`/p/<slug>`) e que republicações de um painel existente atualizem o conteúdo mantendo **exatamente o mesmo endereço público e o mesmo QR Code**.
- **`app/tunnel.py`**: Gerenciador de endereço público de internet. Impede a geração de QR Codes com `localhost`, `127.0.0.1` ou IPs privados. Em ambiente de servidor/nuvem, utiliza o domínio público configurado (`PUBLIC_BASE_URL` ou cabeçalho HTTP público); em execução local, provisiona automaticamente um túnel HTTPS público via **Cloudflare Quick Tunnel (`trycloudflare.com`)**, permitindo acesso imediato por qualquer celular na rede móvel (4G/5G).
- **`app/qr_service.py`**: Geração de QR Codes de alta resolução em PNG Base64 apontando para o endereço público do painel.
- **`app/pdf_service.py` & `templates/pdf_template.html`**: Exportação fiel em **PDF A4 Paisagem** via **Playwright Chromium**, com ajuste automático de tipografia para caber em 1 página (comportando tranquilamente de 1 a 65+ empresas, como no modelo de referência) e paginação automática inteligente caso a quantidade de empresas ou vagas exceda o limite legível de uma única folha.
- **`templates/index.html` & `static/js/app.js`**: Interface administrativa moderna, limpa e responsiva com pré-visualização em tempo real na grade de 7 colunas.
- **`templates/public_panel.html`**: Página pública responsiva para celulares acessada ao escanear o QR Code, sem necessidade de login ou cadastro.

---

## 2. Como Executar

### Execução Direta no Windows
Basta executar o arquivo **`iniciar_sistema.bat`** ou rodar no terminal dentro da pasta do projeto:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Em seguida, abra no navegador:
- **Painel Administrativo:** `http://127.0.0.1:8000`

Ao iniciar, o sistema estabelece automaticamente o endereço público HTTPS (`https://<subdominio>.trycloudflare.com/p/<slug>`) para que os QR Codes gerados funcionem imediatamente em qualquer aparelho celular conectado à internet.

### Hospedagem Permanente em Nuvem / Servidor Institucional
O projeto já inclui `Dockerfile` e `render.yaml` prontos para publicação em **Render**, **Railway**, **Fly.io**, **Google Cloud Run** ou infraestrutura própria do Governo do Paraná / Prefeitura de Curitiba:
- Basta definir a variável de ambiente opcional `PUBLIC_BASE_URL=https://seu-dominio-publico.gov.br` (ou deixar que o sistema detecte automaticamente o domínio HTTPS público da requisição).

---

## 3. Como Executar os Testes Automatizados de Aceitação

```powershell
python -m pytest tests/test_acceptance.py -v
```
