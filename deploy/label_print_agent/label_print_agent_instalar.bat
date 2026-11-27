@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0label_print_agent_install.ps1"
if errorlevel 1 (
  echo Fallo la instalacion. Ejecute como el usuario de LABORATORIO.
  pause
)
