#Requires -Version 5.1
<#
.SYNOPSIS
  Instala el agente de etiquetas para que arranque solo al iniciar sesión.
  Preferencia: tarea programada. Si Acceso denegado: acceso directo en Inicio.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$TaskName = "EMR Label Print Agent"
$StartupName = "EMR Label Print Agent.cmd"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AgentPs1 = Join-Path $ScriptDir "label_print_agent.ps1"
$StartupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$StartupCmd = Join-Path $StartupDir $StartupName

if (-not (Test-Path -LiteralPath $AgentPs1)) {
    throw "No se encontro label_print_agent.ps1 en $ScriptDir"
}

$arg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$AgentPs1`""
$installMode = $null

function Start-AgentNow {
    Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -WorkingDirectory $ScriptDir -ArgumentList $arg | Out-Null
}

function Install-StartupFallback {
    if (-not (Test-Path -LiteralPath $StartupDir)) {
        New-Item -ItemType Directory -Path $StartupDir -Force | Out-Null
    }
    $cmd = @(
        "@echo off",
        "cd /d `"$ScriptDir`"",
        "start `"`" /min powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$AgentPs1`""
    ) -join "`r`n"
    Set-Content -LiteralPath $StartupCmd -Value $cmd -Encoding ASCII
}

# Limpia instalaciones previas (tarea y/o Inicio)
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath $StartupCmd) {
    Remove-Item -LiteralPath $StartupCmd -Force -ErrorAction SilentlyContinue
}

try {
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg -WorkingDirectory $ScriptDir
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -DontStopOnIdleEnd `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -StartWhenAvailable
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Agente USB de etiquetas LIMS (127.0.0.1:18181). No requiere ventana." `
        -Force | Out-Null
    $installMode = "tarea"
    try {
        Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    } catch {
        Start-AgentNow
    }
} catch {
    Write-Host ("Tarea programada no disponible ({0}). Usando carpeta Inicio." -f $_.Exception.Message)
    Install-StartupFallback
    $installMode = "inicio"
    Start-AgentNow
}

Start-Sleep -Seconds 2
$ok = $false
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:18181/health" -UseBasicParsing -TimeoutSec 3
    $ok = ($r.StatusCode -eq 200)
} catch { }

$where = if ($installMode -eq "tarea") {
    "tarea programada 'EMR Label Print Agent'"
} else {
    "carpeta Inicio del usuario ($StartupCmd)"
}

$msg = if ($ok) {
    "Listo. El agente de etiquetas queda instalado ($where) y ya esta corriendo.`n`nSe inicia solo al iniciar sesion en esta PC. No hace falta volver a abrir el .bat.`nLos operadores solo usan Imprimir etiqueta en el EMR."
} else {
    "Quedo registrado el arranque ($where), pero el agente no respondio aun.`n`nCierre sesion y vuelva a entrar, o ejecute label_print_agent.bat una vez para ver el error.`nLog: $ScriptDir\label_print_agent.log"
}

Add-Type -AssemblyName System.Windows.Forms | Out-Null
[System.Windows.Forms.MessageBox]::Show($msg, "EMR - Impresora de etiquetas") | Out-Null
