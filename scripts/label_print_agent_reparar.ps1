#Requires -Version 5.1
<#
.SYNOPSIS
  Detiene el agente viejo, reescribe config TSPL, reinicia y hace selftest.
#>
[CmdletBinding()]
param(
  [string]$AgentDir = 'C:\EMR\label_print_agent',
  [string]$PrinterName = 'EMR ZPL RAW'
)

$ErrorActionPreference = 'Stop'

function Write-Step([string]$msg) {
  Write-Host ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $msg)
}

function Stop-AgentOnPort([int]$Port = 18181) {
  $pids = @()
  try {
    $pids = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
      Select-Object -ExpandProperty OwningProcess -Unique)
  } catch { $pids = @() }
  if (-not $pids -or $pids.Count -eq 0) {
    try {
      $lines = @(netstat -ano | Select-String ":$Port\s+.*LISTENING")
      foreach ($line in $lines) {
        $parts = ($line.ToString() -split '\s+') | Where-Object { $_ }
        if ($parts.Count -ge 5) { $pids += [int]$parts[-1] }
      }
      $pids = @($pids | Select-Object -Unique)
    } catch { }
  }
  foreach ($procId in $pids) {
    if ($procId -le 4) { continue }
    try {
      Write-Step "Deteniendo proceso $procId en puerto $Port"
      Stop-Process -Id $procId -Force -ErrorAction Stop
    } catch {
      Write-Step "No se pudo detener PID $procId : $_"
    }
  }
  Get-Process powershell, pwsh -ErrorAction SilentlyContinue | Where-Object {
    try {
      $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
      $cmd -and ($cmd -match 'label_print_agent\.ps1')
    } catch { $false }
  } | ForEach-Object {
    Write-Step "Deteniendo PowerShell del agente PID $($_.Id)"
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
  }
  Start-Sleep -Seconds 1
}

if (-not (Test-Path -LiteralPath $AgentDir)) {
  throw "No existe $AgentDir. Copie ahi label_print_agent.ps1, EmrRawPrinter.cs y label_print_agent.bat"
}

$ps1 = Join-Path $AgentDir 'label_print_agent.ps1'
$cs = Join-Path $AgentDir 'EmrRawPrinter.cs'
if (-not (Test-Path -LiteralPath $ps1)) { throw "Falta $ps1" }
if (-not (Test-Path -LiteralPath $cs)) { throw "Falta $cs" }

Write-Step "Reparando agente en $AgentDir"
Stop-AgentOnPort 18181

$config = @{
  port = 18181
  printerName = $PrinterName
  language = 'tspl'
  allowedOrigins = @(
    'https://emr.sytes.net:8080',
    'http://emr.sytes.net:8080',
    'http://emr.sytes.net',
    'https://emr.sytes.net',
    'http://dsachubut.sytes.net:8080',
    'https://dsachubut.sytes.net:8080',
    'http://dsachubut.sytes.net',
    'https://dsachubut.sytes.net',
    'http://192.168.10.240',
    'http://192.168.10.240:80',
    'http://192.168.10.240:8080',
    'http://192.168.10.240:3000',
    'http://localhost:3000',
    'http://127.0.0.1:3000'
  )
}
$configPath = Join-Path $AgentDir 'label_print_agent.config.json'
($config | ConvertTo-Json -Depth 4) | Set-Content -LiteralPath $configPath -Encoding UTF8
Write-Step "Config escrita: language=tspl printerName=$PrinterName"

$arg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ps1`""
Start-Process -FilePath 'powershell.exe' -WindowStyle Hidden -WorkingDirectory $AgentDir -ArgumentList $arg | Out-Null
Write-Step 'Agente iniciado'

$health = $null
for ($i = 0; $i -lt 10; $i++) {
  Start-Sleep -Milliseconds 500
  try {
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:18181/health' -TimeoutSec 2
    break
  } catch { }
}

if (-not $health) {
  throw "El agente no responde en http://127.0.0.1:18181/health. Revise $AgentDir\label_print_agent.log"
}

Write-Step ("health ok={0} printer={1} language={2}" -f $health.ok, $health.printer, $health.language)

if (-not $health.ok -or -not $health.printer) {
  throw "Agente vivo pero sin impresora. Verifique que exista la impresora '$PrinterName' (Generic/Text Only RAW)."
}
if (("" + $health.language).ToLowerInvariant() -ne 'tspl') {
  throw "language=$($health.language) (debe ser tspl). Borre config vieja y reejecute este script."
}

try {
  $self = Invoke-RestMethod -Uri 'http://127.0.0.1:18181/selftest' -Method Post -TimeoutSec 8
  Write-Step ("selftest ok printer={0}" -f $self.printer)
} catch {
  throw "Selftest falló: $_. Si la impresora avanzo papel en blanco, confirme puerto USB/RAW."
}

$sampleZpl = @"
^XA
^CI28
^PW320
^LL184
^LH0,0
^FO12,8^A0N,28,14^FDLAB-2026-00018-01^FS
^FO12,40^A0N,18,11^FDPEREZ J. | DNI 30111222^FS
^FO12,62^A0N,16,11^FDGUARDIA^FS
^FO12,82^A0N,16,11^FD14/09 23:00 | EDTA^FS
^XZ
"@

try {
  $r = Invoke-WebRequest -Uri 'http://127.0.0.1:18181/print' -Method Post -ContentType 'text/plain; charset=utf-8' -Body $sampleZpl -UseBasicParsing -TimeoutSec 8
  Write-Step ("print zpl-sample status={0}" -f $r.StatusCode)
} catch {
  throw "Prueba ZPL->TSPL falló: $_"
}

Write-Host ''
Write-Host 'OK: agente TSPL listo. Deberia haber salido etiqueta EMR OK + muestra LAB-2026-00018-01.'
Write-Host 'Ahora pruebe Imprimir etiqueta en https://emr.sytes.net:8080'
Write-Host ("Log: {0}\label_print_agent.log" -f $AgentDir)
