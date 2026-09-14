#Requires -Version 5.1
<#
.SYNOPSIS
  Agente local de impresión ZPL para etiquetas LIMS (3nStar LDT114 USB).

.DESCRIPTION
  Escucha SOLO en http://127.0.0.1:18181 (nunca en la red).
  El navegador del EMR envía el ZPL; este proceso lo manda RAW a la
  impresora Windows instalada en ESTA PC.

  Instalación (PC LABORATORIO, una vez):
    Ejecutar label_print_agent_instalar.bat
    Queda como tarea de Windows (inicio de sesión, sin ventana).
    Opcional: label_print_agent.config.json al lado de este .ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigPath = Join-Path $ScriptDir "label_print_agent.config.json"
$LogPath = Join-Path $ScriptDir "label_print_agent.log"
$ListenHost = "127.0.0.1"
$Port = 18181
$PrinterNameOverride = ""
$AllowedOrigins = @(
    "http://192.168.10.240",
    "http://192.168.10.240:80",
    "http://192.168.10.240:8080",
    "http://192.168.10.240:3000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
)

if (Test-Path -LiteralPath $ConfigPath) {
    try {
        $cfg = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($cfg.port) { $Port = [int]$cfg.port }
        if ($cfg.printerName) { $PrinterNameOverride = [string]$cfg.printerName }
        if ($cfg.allowedOrigins) {
            $AllowedOrigins = @($cfg.allowedOrigins | ForEach-Object { [string]$_ })
        }
    } catch {
        Write-Warning "No se pudo leer $ConfigPath — se usan valores por defecto. $_"
    }
}

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public class EmrRawPrinter {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi)]
    public class DOCINFOA {
        [MarshalAs(UnmanagedType.LPStr)] public string pDocName;
        [MarshalAs(UnmanagedType.LPStr)] public string pOutputFile;
        [MarshalAs(UnmanagedType.LPStr)] public string pDataType;
    }

    [DllImport("winspool.Drv", EntryPoint = "OpenPrinterA", SetLastError = true,
        CharSet = CharSet.Ansi, ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool OpenPrinter([MarshalAs(UnmanagedType.LPStr)] string szPrinter, out IntPtr hPrinter, IntPtr pd);

    [DllImport("winspool.Drv", EntryPoint = "ClosePrinter", SetLastError = true,
        ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool ClosePrinter(IntPtr hPrinter);

    [DllImport("winspool.Drv", EntryPoint = "StartDocPrinterA", SetLastError = true,
        CharSet = CharSet.Ansi, ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool StartDocPrinter(IntPtr hPrinter, int level, [In, MarshalAs(UnmanagedType.LPStruct)] DOCINFOA di);

    [DllImport("winspool.Drv", EntryPoint = "EndDocPrinter", SetLastError = true,
        ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool EndDocPrinter(IntPtr hPrinter);

    [DllImport("winspool.Drv", EntryPoint = "StartPagePrinter", SetLastError = true,
        ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool StartPagePrinter(IntPtr hPrinter);

    [DllImport("winspool.Drv", EntryPoint = "EndPagePrinter", SetLastError = true,
        ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool EndPagePrinter(IntPtr hPrinter);

    [DllImport("winspool.Drv", EntryPoint = "WritePrinter", SetLastError = true,
        ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool WritePrinter(IntPtr hPrinter, IntPtr pBytes, int dwCount, out int dwWritten);

    public static void SendBytes(string printerName, byte[] bytes) {
        IntPtr hPrinter = IntPtr.Zero;
        IntPtr pBytes = IntPtr.Zero;
        try {
            if (!OpenPrinter(printerName.Normalize(), out hPrinter, IntPtr.Zero)) {
                throw new Exception("OpenPrinter failed: " + Marshal.GetLastWin32Error());
            }
            DOCINFOA di = new DOCINFOA();
            di.pDocName = "EMR label";
            di.pDataType = "RAW";
            if (!StartDocPrinter(hPrinter, 1, di)) {
                throw new Exception("StartDocPrinter failed: " + Marshal.GetLastWin32Error());
            }
            try {
                if (!StartPagePrinter(hPrinter)) {
                    throw new Exception("StartPagePrinter failed: " + Marshal.GetLastWin32Error());
                }
                try {
                    pBytes = Marshal.AllocHGlobal(bytes.Length);
                    Marshal.Copy(bytes, 0, pBytes, bytes.Length);
                    int written;
                    if (!WritePrinter(hPrinter, pBytes, bytes.Length, out written)) {
                        throw new Exception("WritePrinter failed: " + Marshal.GetLastWin32Error());
                    }
                } finally {
                    EndPagePrinter(hPrinter);
                }
            } finally {
                EndDocPrinter(hPrinter);
            }
        } finally {
            if (pBytes != IntPtr.Zero) { Marshal.FreeHGlobal(pBytes); }
            if (hPrinter != IntPtr.Zero) { ClosePrinter(hPrinter); }
        }
    }
}
'@ -ErrorAction Stop

function Get-InstalledPrinterNames {
    $names = @()
    try {
        $names = @(Get-CimInstance -ClassName Win32_Printer -ErrorAction Stop | ForEach-Object { $_.Name })
    } catch {
        try {
            $names = @(Get-Printer -ErrorAction Stop | ForEach-Object { $_.Name })
        } catch {
            $names = @()
        }
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
    $match = $all | Where-Object { $_ -match '3nStar|LDT114|ZDesigner' } | Select-Object -First 1
    if ($match) { return [string]$match }
    return $null
}

function Test-AllowedOrigin([string]$origin) {
    if (-not $origin) { return $false }
    foreach ($o in $AllowedOrigins) {
        if ($origin -eq $o) { return $true }
    }
    return $false
}

function Write-JsonResponse {
    param(
        [Parameter(Mandatory = $true)][System.Net.HttpListenerResponse]$Response,
        [Parameter(Mandatory = $true)][int]$Status,
        [Parameter(Mandatory = $true)]$Body,
        [string]$Origin = ""
    )
    $json = $Body | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    if (Test-AllowedOrigin $Origin) {
        $Response.Headers.Add("Access-Control-Allow-Origin", $Origin)
        $Response.Headers.Add("Vary", "Origin")
        $Response.Headers.Add("Access-Control-Allow-Private-Network", "true")
    }
    $Response.Headers.Add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    $Response.Headers.Add("Access-Control-Allow-Headers", "Content-Type")
    $Response.StatusCode = $Status
    $Response.ContentType = "application/json; charset=utf-8"
    $Response.ContentLength64 = $bytes.Length
    $Response.OutputStream.Write($bytes, 0, $bytes.Length)
}

function Write-EmptyCors {
    param(
        [Parameter(Mandatory = $true)][System.Net.HttpListenerResponse]$Response,
        [Parameter(Mandatory = $true)][int]$Status,
        [string]$Origin = ""
    )
    if (Test-AllowedOrigin $Origin) {
        $Response.Headers.Add("Access-Control-Allow-Origin", $Origin)
        $Response.Headers.Add("Vary", "Origin")
        $Response.Headers.Add("Access-Control-Allow-Private-Network", "true")
    }
    $Response.Headers.Add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    $Response.Headers.Add("Access-Control-Allow-Headers", "Content-Type")
    $Response.Headers.Add("Access-Control-Max-Age", "600")
    $Response.StatusCode = $Status
    $Response.ContentLength64 = 0
}

function Write-AgentLog([string]$msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    try { Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8 } catch { }
    Write-Host $line
}

function Read-RequestBody([System.Net.HttpListenerRequest]$Request) {
    if ($Request.ContentLength64 -eq 0) { return "" }
    $reader = New-Object System.IO.StreamReader($Request.InputStream, [System.Text.Encoding]::UTF8)
    try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
}

$prefix = "http://${ListenHost}:${Port}/"
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add($prefix)

try {
    $listener.Start()
} catch {
    Write-AgentLog "Puerto ocupado o agente ya en marcha: $prefix — $_"
    exit 0
}

$resolved = $null
try { $resolved = Resolve-LabelPrinterName } catch { Write-AgentLog "$_" }

Write-AgentLog "Agente en $prefix impresora=$(if ($resolved) { $resolved } else { 'NO DETECTADA' })"

try {
    while ($listener.IsListening) {
        $ctx = $listener.GetContext()
        $req = $ctx.Request
        $res = $ctx.Response
        $origin = [string]$req.Headers["Origin"]
        $path = $req.Url.AbsolutePath.TrimEnd("/").ToLowerInvariant()
        if (-not $path) { $path = "/" }

        try {
            if ($req.HttpMethod -eq "OPTIONS") {
                Write-EmptyCors -Response $res -Status 204 -Origin $origin
                continue
            }

            if ($req.HttpMethod -eq "GET" -and ($path -eq "/health" -or $path -eq "/")) {
                $printer = $null
                $err = $null
                try {
                    $printer = Resolve-LabelPrinterName
                } catch {
                    $err = [string]$_.Exception.Message
                }
                $ok = [bool]$printer
                Write-JsonResponse -Response $res -Status 200 -Origin $origin -Body @{
                    ok      = $ok
                    printer = $printer
                    error   = $(if ($ok) { $null } elseif ($err) { $err } else { "no_printer" })
                }
                continue
            }

            if ($req.HttpMethod -eq "POST" -and $path -eq "/print") {
                $printer = $null
                try {
                    $printer = Resolve-LabelPrinterName
                } catch {
                    Write-JsonResponse -Response $res -Status 400 -Origin $origin -Body @{
                        ok = $false; error = "no_printer"; message = [string]$_.Exception.Message
                    }
                    continue
                }
                if (-not $printer) {
                    Write-JsonResponse -Response $res -Status 400 -Origin $origin -Body @{
                        ok = $false; error = "no_printer"; message = "No se encontro impresora de etiquetas en esta PC."
                    }
                    continue
                }
                $zpl = Read-RequestBody $req
                if (-not $zpl -or ($zpl.Trim().Length -lt 4)) {
                    Write-JsonResponse -Response $res -Status 400 -Origin $origin -Body @{
                        ok = $false; error = "empty_zpl"; message = "No hay datos para imprimir."
                    }
                    continue
                }
                try {
                    $bytes = [System.Text.Encoding]::UTF8.GetBytes($zpl)
                    [EmrRawPrinter]::SendBytes($printer, $bytes)
                    Write-JsonResponse -Response $res -Status 200 -Origin $origin -Body @{
                        ok = $true; printer = $printer
                    }
                } catch {
                    Write-JsonResponse -Response $res -Status 500 -Origin $origin -Body @{
                        ok = $false; error = "print_failed"; message = "No se pudo enviar a la impresora."
                    }
                }
                continue
            }

            Write-JsonResponse -Response $res -Status 404 -Origin $origin -Body @{
                ok = $false; error = "not_found"
            }
        } catch {
            try {
                Write-JsonResponse -Response $res -Status 500 -Origin $origin -Body @{
                    ok = $false; error = "internal"
                }
            } catch { }
        } finally {
            try { $res.OutputStream.Close() } catch { }
            try { $res.Close() } catch { }
        }
    }
} finally {
    if ($listener.IsListening) { $listener.Stop() }
    $listener.Close()
}
