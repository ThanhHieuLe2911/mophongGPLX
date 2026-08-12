$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    py -3.12 -m venv (Join-Path $projectRoot ".venv") 2>$null
    if (-not (Test-Path -LiteralPath $venvPython)) {
        py -3.13 -m venv (Join-Path $projectRoot ".venv")
    }
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $projectRoot "requirements-dev.txt")

Write-Host "Da san sang. Chay .\scripts\run.ps1"

