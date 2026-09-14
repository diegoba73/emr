@echo off
REM Uso manual / diagnostico (deja una ventana abierta).
REM En LABORATORIO el flujo normal es label_print_agent_instalar.bat (una vez).
title EMR - Agente impresora de etiquetas
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0label_print_agent.ps1"
if errorlevel 1 pause
