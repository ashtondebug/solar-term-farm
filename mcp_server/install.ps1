# Install the AgriVerse MCP bridge into a local Windows virtual environment.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $Root ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"

if (-not (Test-Path $Python)) {
    py -3 -m venv --system-site-packages $Venv
}
& $Python -m pip install --upgrade pip
& $Python -m pip install --no-build-isolation -e $Root
if ($LASTEXITCODE -ne 0) {
    throw "MCP package installation failed"
}

Write-Host "Installed. Run: $Root\run.ps1"
Write-Host "Then add mcp.example.json to your MCP client configuration."

