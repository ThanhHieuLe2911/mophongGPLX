$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Chua co .venv. Hay chay .\scripts\setup.ps1 truoc."
}

$env:PYTHONPATH = Join-Path $projectRoot "src"
& $python -m gplx_sim.main

