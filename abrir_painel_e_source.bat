@echo off
setlocal

cd /d "%~dp0"

set "BASE_URL=http://127.0.0.1:5500"
set "PANEL_URL=%BASE_URL%/obs_control_panel.html"
set "SOURCE_URL=%BASE_URL%/obs_lower_thirds_source.html"

echo Verificando servidor local em %BASE_URL% ...
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri '%BASE_URL%' -UseBasicParsing -TimeoutSec 2; exit 0 } catch { exit 1 }"

if errorlevel 1 (
  echo Servidor nao detectado. Iniciando em nova janela...
  start "Servidor Lower Thirds" cmd /k "cd /d "%~dp0" && call iniciar_servidor_local.bat"
  timeout /t 2 /nobreak >nul
)

echo Abrindo painel e source no navegador padrao...
start "" "%PANEL_URL%"
start "" "%SOURCE_URL%"

echo.
echo Painel: %PANEL_URL%
echo Source: %SOURCE_URL%
echo.
echo Pronto.
