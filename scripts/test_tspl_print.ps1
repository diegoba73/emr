#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$Dir = 'C:\EMR\label_print_agent'
$cs = Get-Content -LiteralPath (Join-Path $Dir 'EmrRawPrinter.cs') -Raw -Encoding UTF8
Add-Type -TypeDefinition $cs -ErrorAction Stop
$tspl = @"
SIZE 40 mm,23 mm
GAP 2 mm,0
DENSITY 10
DIRECTION 1
CLS
TEXT 30,40,"2",0,1,1,"HOLA EMR"
PRINT 1,1
"@
[EmrRawPrinter]::SendBytes('EMR ZPL RAW', [Text.Encoding]::UTF8.GetBytes($tspl))
Write-Host 'TSPL de prueba enviado a EMR ZPL RAW'
