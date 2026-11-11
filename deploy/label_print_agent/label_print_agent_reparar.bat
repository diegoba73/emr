@echo off
title EMR - Reparar agente impresora
cd /d "%~dp0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0label_print_agent_reparar.ps1" -AgentDir "%~dp0"
if errorlevel 1 (
  echo.
  echo FALLO. Revise label_print_agent.log
  pause
  exit /b 1
)
echo.
pause
