$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Chua co .venv. Hay chay .\scripts\setup.ps1 truoc."
}

Push-Location $projectRoot
try {
    $env:PYTHONPATH = Join-Path $projectRoot "src"
    & $python -c "from gplx_sim.bootstrap import initialize_databases; from gplx_sim.paths import AppPaths; initialize_databases(AppPaths.discover())"

    & $python -m PyInstaller `
        --noconfirm `
        --clean `
        --windowed `
        --onedir `
        --name MoPhongGPLX `
        --contents-directory _internal `
        --paths "src" `
        --add-data "src/gplx_sim/data;gplx_sim/data" `
        --add-data "src/gplx_sim/resources;gplx_sim/resources" `
        "src/gplx_sim/main.py"

    $contentDestination = Join-Path $projectRoot "dist\MoPhongGPLX\content"
    New-Item -ItemType Directory -Force -Path $contentDestination | Out-Null
    Copy-Item -LiteralPath (Join-Path $projectRoot "content\content.db") -Destination $contentDestination -Force
    Copy-Item -LiteralPath (Join-Path $projectRoot "content\videos") -Destination $contentDestination -Recurse -Force
    Write-Host "Build hoan tat: dist\MoPhongGPLX"
}
finally {
    Pop-Location
}
