$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$database = Join-Path $projectRoot "content\bundled_content.db"
$videos = Join-Path $projectRoot "content\videos"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Chua co .venv. Hay chay .\scripts\setup.ps1 truoc."
}

$env:PYTHONPATH = Join-Path $projectRoot "src"
& $python -m gplx_sim.data_builder $database
& $python -m gplx_sim.content_validation $database $videos
