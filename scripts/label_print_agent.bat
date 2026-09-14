@echo off
title EMR - Agente impresora de etiquetas
cd /d "%~dp0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0label_print_agent.ps1"
if errorlevel 1 pause
