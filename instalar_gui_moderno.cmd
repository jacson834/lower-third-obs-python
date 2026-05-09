@echo off
setlocal

cd /d "%~dp0"

echo Instalando dependencias da GUI moderna...
echo.

py -m pip install --upgrade pip
py -m pip install PySide6 qrcode pillow

if errorlevel 1 (
  echo.
  echo Falha com "py". Tentando com "python"...
  python -m pip install --upgrade pip
  python -m pip install PySide6 qrcode pillow
)

echo.
echo Concluido.
pause

endlocal
