@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo  Scharff Transcricao — faster-whisper large-v3 + GPU
echo  Coloque os arquivos em "entrada\" e aguarde.
echo  (1a vez baixa o modelo ~1.5GB, depois e offline)
echo ============================================================
echo.
python "%~dp0transcrever.py" %*
echo.
echo ============================================================
echo  Pronto! Resultados em "saida\"
echo  Avise o Claude que os arquivos estao prontos.
echo ============================================================
pause
