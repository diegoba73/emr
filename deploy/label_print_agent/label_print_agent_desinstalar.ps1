#Requires -Version 5.1
$ErrorActionPreference = "SilentlyContinue"
$TaskName = "EMR Label Print Agent"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object {
    $_.CommandLine -like '*label_print_agent.ps1*'
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.MessageBox]::Show("Agente de etiquetas desinstalado.", "EMR") | Out-Null
