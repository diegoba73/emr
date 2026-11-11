@echo off
title EMR - Impresoras instaladas en esta PC
cd /d "%~dp0"
echo.
echo Impresoras que ve Windows en esta PC:
echo ------------------------------------
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -Command ^
  "Get-CimInstance Win32_Printer | Sort-Object Name | ForEach-Object { $_.Name }"
echo.
echo Si ninguna contiene 4BARCODE / 4B-2054 / EMR ZPL RAW / 3nStar / LDT114 / ZDesigner,
echo edite label_print_agent.config.json y ponga el nombre exacto en printerName.
echo.
pause
