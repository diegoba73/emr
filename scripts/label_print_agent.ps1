$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigPath = Join-Path $ScriptDir 'label_print_agent.config.json'
$LogPath = Join-Path $ScriptDir 'label_print_agent.log'
$ListenHost = '127.0.0.1'
$Port = 18181
$PrinterNameOverride = ''
$PrinterLanguage = 'tspl'
$AllowedOrigins = @(
  'https://emr.sytes.net:8080',
  'http://emr.sytes.net:8080',
  'http://emr.sytes.net',
  'https://emr.sytes.net',
  'http://192.168.10.240',
  'http://192.168.10.240:80',
  'http://192.168.10.240:8080',
  'http://192.168.10.240:3000',
  'http://localhost:3000',
  'http://127.0.0.1:3000',
  'http://localhost:8000',
  'http://127.0.0.1:8000'
)

if (Test-Path -LiteralPath $ConfigPath) {
  try {
    $cfg = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($cfg.port) { $Port = [int]$cfg.port }
    if ($cfg.printerName) { $PrinterNameOverride = [string]$cfg.printerName }
    if ($cfg.language) { $PrinterLanguage = ([string]$cfg.language).Trim().ToLowerInvariant() }
    if ($cfg.allowedOrigins) { $AllowedOrigins = @($cfg.allowedOrigins | ForEach-Object { [string]$_ }) }
  } catch {
    Write-Host "WARN config: $_"
  }
}

$CsPath = Join-Path $ScriptDir 'EmrRawPrinter.cs'
if (-not (Test-Path -LiteralPath $CsPath)) { throw "Falta EmrRawPrinter.cs en $ScriptDir" }
try {
  Add-Type -TypeDefinition (Get-Content -LiteralPath $CsPath -Raw -Encoding UTF8) -ErrorAction Stop
} catch {
  if ($_.Exception.Message -notmatch 'already exists') { throw }
}

function Get-InstalledPrinterNames {
  $names = @()
  try { $names = @(Get-CimInstance -ClassName Win32_Printer -ErrorAction Stop | ForEach-Object { $_.Name }) } catch {
    try { $names = @(Get-Printer -ErrorAction Stop | ForEach-Object { $_.Name }) } catch { $names = @() }
  }
  return @($names | Where-Object { $_ })
}

function Resolve-LabelPrinterName {
  if ($PrinterNameOverride -and $PrinterNameOverride.Trim()) {
    $want = $PrinterNameOverride.Trim()
    $all = Get-InstalledPrinterNames
    if ($all -contains $want) { return $want }
    throw "Impresora configurada no encontrada: $want"
  }
  $all = Get-InstalledPrinterNames
  $match = $all | Where-Object { $_ -match '3nStar|LDT114|ZDesigner|4BARCODE|4B-2054|EMR ZPL RAW' } | Select-Object -First 1
  if ($match) { return [string]$match }
  return $null
}

function Test-AllowedOrigin([string]$origin) {
  if (-not $origin) { return $false }
  foreach ($o in $AllowedOrigins) { if ($origin -eq $o) { return $true } }
  return $false
}

function Write-JsonResponse {
  param($Response, [int]$Status, $Body, [string]$Origin = '')
  $json = $Body | ConvertTo-Json -Compress
  $bytes = [Text.Encoding]::UTF8.GetBytes($json)
  if (Test-AllowedOrigin $Origin) {
    $Response.Headers['Access-Control-Allow-Origin'] = $Origin
    $Response.Headers['Vary'] = 'Origin'
    $Response.Headers['Access-Control-Allow-Private-Network'] = 'true'
  }
  $Response.Headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
  $Response.Headers['Access-Control-Allow-Headers'] = 'Content-Type'
  $Response.StatusCode = $Status
  $Response.ContentType = 'application/json; charset=utf-8'
  $Response.ContentLength64 = $bytes.Length
  $Response.OutputStream.Write($bytes, 0, $bytes.Length)
}

function Write-EmptyCors {
  param($Response, [int]$Status, [string]$Origin = '')
  if (Test-AllowedOrigin $Origin) {
    $Response.Headers['Access-Control-Allow-Origin'] = $Origin
    $Response.Headers['Vary'] = 'Origin'
    $Response.Headers['Access-Control-Allow-Private-Network'] = 'true'
  }
  $Response.Headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
  $Response.Headers['Access-Control-Allow-Headers'] = 'Content-Type'
  $Response.Headers['Access-Control-Max-Age'] = '600'
  $Response.StatusCode = $Status
  $Response.ContentLength64 = 0
}

function Write-AgentLog([string]$msg) {
  $line = '[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
  try { Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8 } catch {}
  Write-Host $line
}

function Read-RequestBody($Request) {
  if ($Request.ContentLength64 -eq 0) { return '' }
  $reader = New-Object IO.StreamReader($Request.InputStream, [Text.Encoding]::UTF8)
  try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
}

function Convert-ZplToTspl([string]$Zpl) {
  $fields = [regex]::Matches($Zpl, '\^FD(.*?)\^FS') | ForEach-Object { $_.Groups[1].Value }
  if (-not $fields -or $fields.Count -eq 0) { throw 'No se pudieron leer campos FD del ZPL' }
  $sb = New-Object Text.StringBuilder
  [void]$sb.AppendLine('SIZE 40 mm,23 mm')
  [void]$sb.AppendLine('GAP 2 mm,0')
  [void]$sb.AppendLine('DENSITY 10')
  [void]$sb.AppendLine('DIRECTION 1')
  [void]$sb.AppendLine('CLS')
  $y = 8
  for ($i = 0; $i -lt $fields.Count; $i++) {
    $text = ($fields[$i] -replace '"', "'")
    if ($i -eq 0) {
      [void]$sb.AppendLine(('BARCODE 12,8,"128",36,0,0,1,2,"{0}"' -f $text))
      $y = 52
      [void]$sb.AppendLine(('TEXT 12,{0},"2",0,1,1,"{1}"' -f $y, $text))
      $y = 78
    } else {
      [void]$sb.AppendLine(('TEXT 12,{0},"1",0,1,1,"{1}"' -f $y, $text))
      $y += 26
    }
  }
  [void]$sb.AppendLine('PRINT 1,1')
  return $sb.ToString()
}

function Convert-PrintPayload([string]$Payload) {
  if ($PrinterLanguage -eq 'tspl' -or $PrinterLanguage -eq 'tsp') {
    return Convert-ZplToTspl $Payload
  }
  return $Payload
}

$prefix = "http://${ListenHost}:${Port}/"
$listener = New-Object Net.HttpListener
$listener.Prefixes.Add($prefix)
try { $listener.Start() } catch { Write-AgentLog "Puerto ocupado o agente ya en marcha: $prefix - $_"; exit 0 }

$resolved = $null
try { $resolved = Resolve-LabelPrinterName } catch { Write-AgentLog "$_" }
Write-AgentLog "Agente en $prefix impresora=$(if ($resolved) { $resolved } else { 'NO DETECTADA' }) language=$PrinterLanguage"

try {
  while ($listener.IsListening) {
    $ctx = $listener.GetContext()
    $req = $ctx.Request
    $res = $ctx.Response
    $origin = [string]$req.Headers['Origin']
    $path = $req.Url.AbsolutePath.TrimEnd('/').ToLowerInvariant()
    if (-not $path) { $path = '/' }
    try {
      if ($req.HttpMethod -eq 'OPTIONS') { Write-EmptyCors $res 204 $origin; continue }

      if ($req.HttpMethod -eq 'GET' -and ($path -eq '/health' -or $path -eq '/')) {
        $printer = $null; $err = $null
        try { $printer = Resolve-LabelPrinterName } catch { $err = [string]$_.Exception.Message }
        $ok = [bool]$printer
        Write-JsonResponse $res 200 @{ ok = $ok; printer = $printer; error = $(if ($ok) { $null } elseif ($err) { $err } else { 'no_printer' }); language = $PrinterLanguage } $origin
        continue
      }

      if ($req.HttpMethod -eq 'POST' -and $path -eq '/print') {
        $printer = $null
        try { $printer = Resolve-LabelPrinterName } catch {
          Write-JsonResponse $res 400 @{ ok = $false; error = 'no_printer'; message = [string]$_.Exception.Message } $origin
          continue
        }
        if (-not $printer) {
          Write-JsonResponse $res 400 @{ ok = $false; error = 'no_printer'; message = 'No se encontro impresora de etiquetas en esta PC.' } $origin
          continue
        }
        $zpl = Read-RequestBody $req
        if (-not $zpl -or ($zpl.Trim().Length -lt 4)) {
          Write-JsonResponse $res 400 @{ ok = $false; error = 'empty_zpl'; message = 'No hay datos para imprimir.' } $origin
          continue
        }
        try {
          $payload = Convert-PrintPayload $zpl
          $bytes = [Text.Encoding]::UTF8.GetBytes($payload)
          [EmrRawPrinter]::SendBytes($printer, $bytes)
          Write-JsonResponse $res 200 @{ ok = $true; printer = $printer; language = $PrinterLanguage } $origin
        } catch {
          Write-AgentLog ("print_failed: " + $_.Exception.Message)
          Write-JsonResponse $res 500 @{ ok = $false; error = 'print_failed'; message = 'No se pudo enviar a la impresora.' } $origin
        }
        continue
      }

      Write-JsonResponse $res 404 @{ ok = $false; error = 'not_found' } $origin
    } catch {
      try { Write-JsonResponse $res 500 @{ ok = $false; error = 'internal' } $origin } catch {}
    } finally {
      try { $res.OutputStream.Close() } catch {}
      try { $res.Close() } catch {}
    }
  }
} finally {
  if ($listener.IsListening) { $listener.Stop() }
  $listener.Close()
}
