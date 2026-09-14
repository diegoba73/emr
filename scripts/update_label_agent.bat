@echo off
set DIR=C:\EMR\label_print_agent
if not exist "%DIR%" mkdir "%DIR%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; =New-Object Net.WebClient; .Encoding=[Text.Encoding]::UTF8; .DownloadFile('https://raw.githubusercontent.com/diegoba73/emr/b0fc2167f814d517c31971e4d25222156ef7142b/scripts/label_print_agent.ps1','%DIR%\label_print_agent.ps1'); [ordered]@{port=18181;printerName='EMR ZPL RAW';language='tspl';allowedOrigins=@('https://emr.sytes.net:8080','http://emr.sytes.net:8080','http://192.168.10.240','http://192.168.10.240:8080')} | ConvertTo-Json | Set-Content -Encoding UTF8 '%DIR%\label_print_agent.config.json'; Write-Host UPDATED; Get-Content '%DIR%\label_print_agent.config.json'"
echo.
echo Ahora ejecuta: %DIR%\label_print_agent.bat
pause
