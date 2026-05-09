@echo off
setlocal

cd /d "%~dp0"

echo Iniciando servidor local em http://127.0.0.1:5500
echo.
echo URLs:
echo  - Painel: http://127.0.0.1:5500/obs_control_panel.html
echo  - Source: http://127.0.0.1:5500/obs_lower_thirds_source.html
echo.
echo Para parar, feche esta janela ou pressione Ctrl+C.
echo.

py -m http.server 5500

if errorlevel 1 (
  echo.
  echo Erro ao iniciar com "py". Tentando com "python"...
  python -m http.server 5500
)

echo.
echo Servidor finalizado.
pause
