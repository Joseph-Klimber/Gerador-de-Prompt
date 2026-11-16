@echo off
chcp 65001 > nul
title Prompt Studio Cockpit

cd /d "%~dp0"

echo ===================================================
echo   Prompt Studio Cockpit - Versao Local (Backup D:)
echo ===================================================
echo.
echo [1/2] Abrindo o navegador em http://localhost:8501...
start "" "http://localhost:8501"

echo [2/2] Iniciando servidor do aplicativo...
echo.
echo Mantenha esta janela aberta enquanto usar o app.
echo Pressione Ctrl+C para encerrar.
echo ---------------------------------------------------
echo.

".venv\Scripts\python.exe" -m streamlit run app.py --server.headless true --server.port 8501

pause
