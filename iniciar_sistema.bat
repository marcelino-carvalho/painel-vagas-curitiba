@echo off
chcp 65001 > nul
echo ============================================================================
echo   SISTEMA DE CRIACAO DE PAINEL DE VAGAS - AGENCIA DO TRABALHADOR DE CURITIBA
echo ============================================================================
echo Iniciando servidor web e tunel publico para QR Code...
echo Acesse no navegador: http://127.0.0.1:8000
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
