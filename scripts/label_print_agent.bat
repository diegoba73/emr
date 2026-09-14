@echo off
title EMR - Agente impresora de etiquetas
cd /d "%~dp0"
REM Si ya hay un agente viejo en 18181, el .ps1 sale sin error y NO se actualiza.
REM Preferir label_print_agent_reparar.bat tras cambiar archivos.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0label_print_agent.ps1"
if errorlevel 1 pause
