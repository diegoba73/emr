# Actualiza .env con la IPv4 Wi-Fi actual y reinicia el backend Docker.
# Uso (PowerShell, desde la raíz del repo o cualquier lado):
#   powershell -ExecutionPolicy Bypass -File scripts\sync_lan_ip.ps1
#
# Garantiza que kiosco / TV / celular no queden apuntando a una IP vieja.

$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
  if ($PSScriptRoot) {
    return (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
  }
  return (Get-Location).Path
}

function Get-WifiIpv4 {
  # Preferí Ethernet/Wi-Fi físicas con 192.168.* (en esta PC a veces el kiosco
  # llega por Ethernet y Wi-Fi queda con IP vieja o sin IPv4).
  $candidates = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
      $_.IPAddress -like '192.168.*' -and
      $_.PrefixOrigin -ne 'WellKnown' -and
      $_.InterfaceAlias -notmatch 'vEthernet|WSL|Hyper-V|Virtual|Loopback|Bluetooth|Wi-Fi Direct|Local Area Connection\*'
    } |
    Sort-Object -Property @{
      Expression = {
        if ($_.InterfaceAlias -match 'Ethernet') { 0 }
        elseif ($_.InterfaceAlias -match 'Wi-?Fi|WLAN|Wireless') { 1 }
        else { 2 }
      }
    }, InterfaceIndex
  if ($candidates) { return $candidates[0].IPAddress }
  return $null
}

function Set-EnvLan([string]$envPath, [string]$ip, [int]$frontendPort = 3000) {
  if (-not (Test-Path $envPath)) {
    throw "No existe $envPath"
  }
  $origin = "http://${ip}:${frontendPort}"
  $devHosts = "localhost,127.0.0.1,0.0.0.0,backend,$ip"
  $allowed = "localhost,127.0.0.1,0.0.0.0,$ip"

  $text = Get-Content -Raw -Path $envPath
  $replacements = @{
    '(?m)^DJANGO_ALLOWED_HOSTS=.*$'     = "DJANGO_ALLOWED_HOSTS=$allowed"
    '(?m)^EMR_LAN_IPS=.*$'              = "EMR_LAN_IPS=$ip"
    '(?m)^EMR_KIOSCO_LAN_ORIGIN=.*$'    = "EMR_KIOSCO_LAN_ORIGIN=$origin"
    '(?m)^EMR_DEV_ALLOWED_HOSTS=.*$'    = "EMR_DEV_ALLOWED_HOSTS=$devHosts"
  }
  foreach ($pat in $replacements.Keys) {
    if ($text -match $pat) {
      $text = [regex]::Replace($text, $pat, $replacements[$pat])
    } else {
      $text = $text.TrimEnd() + "`n" + $replacements[$pat] + "`n"
    }
  }
  Set-Content -Path $envPath -Value $text -NoNewline -Encoding UTF8
}

$root = Get-RepoRoot
$envFile = Join-Path $root '.env'
$ip = Get-WifiIpv4
if (-not $ip) {
  Write-Error 'No se detectó IPv4 Wi-Fi (192.168.x). Conectate a la red de la clínica e intentá de nuevo.'
}

Write-Host "IP Wi-Fi detectada: $ip"
Set-EnvLan -envPath $envFile -ip $ip
Write-Host "Actualizado: $envFile"

Push-Location $root
try {
  wsl -d Ubuntu -- bash -lc "cd /home/diego/proyectos/emr && docker compose up -d backend"
  Write-Host "Backend recreado con EMR_LAN_IPS=$ip"
  Write-Host ""
  Write-Host "URLs:"
  Write-Host "  Kiosco:     http://${ip}:3000/kiosco-recepcion"
  Write-Host "  TV:         http://${ip}:3000/pantalla-sala"
  Write-Host "  Recepción:  http://${ip}:3000/recepcion"
  Write-Host "  QR anuncio: http://${ip}:3000/recepcion/qr-anuncio"
} finally {
  Pop-Location
}
