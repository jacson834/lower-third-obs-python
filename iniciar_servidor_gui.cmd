@echo off
setlocal

cd /d "%~dp0"

echo Iniciando interface do servidor local...

py servidor_local_gui.py
if errorlevel 1 (
  echo.
  echo Falha com "py". Tentando com "python"...
  python servidor_local_gui.py
)

endlocal
