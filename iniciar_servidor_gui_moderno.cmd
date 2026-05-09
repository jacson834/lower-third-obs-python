@echo off
setlocal

cd /d "%~dp0"

echo Iniciando GUI moderna...
py servidor_local_gui_moderno.py
if errorlevel 1 (
  echo.
  echo Falha com "py". Tentando com "python"...
  python servidor_local_gui_moderno.py
)

if errorlevel 1 (
  echo.
  echo A GUI moderna precisa das dependencias Python.
  echo Instale com:
  echo   pip install PySide6
  echo.
)

pause

endlocal
