# AgriVerse MCP Server for Windows
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $Root ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "Creating virtual environment..."
    py -3 -m venv $Venv
    & $Python -m pip install --upgrade pip
    & $Python -m pip install -e $Root
}

if (-not $env:AGRI_BASE_URL) { $env:AGRI_BASE_URL = "http://192.168.153.234" }
if (-not $env:AGRI_ALLOW_CONTROL) { $env:AGRI_ALLOW_CONTROL = "0" }
if (-not $env:AGRI_TIMEOUT_S) { $env:AGRI_TIMEOUT_S = "8" }

Write-Host "AgriVerse MCP: $env:AGRI_BASE_URL  control=$env:AGRI_ALLOW_CONTROL"
& $Python -m agriverse_mcp --transport stdio

