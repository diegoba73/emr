@echo off
title EMR - Agente impresora de etiquetas
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0label_print_agent.ps1"
if errorlevel 1 pause
