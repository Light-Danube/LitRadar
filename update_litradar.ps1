$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path (Join-Path $PSScriptRoot '.git'))) {
    Write-Error 'This folder is not a Git checkout. Clone/publish the repository first, then use GitHub Desktop or this updater.'
    exit 2
}
$dirty = git status --porcelain
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($dirty) {
    Write-Host 'Update stopped: there are local tracked changes.' -ForegroundColor Yellow
    Write-Host 'Commit or stash them in GitHub Desktop, then run this script again.'
    Write-Host 'Local database, offline files, source cache, and .env are ignored and are not the cause of this check.'
    exit 3
}
git pull --ff-only
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$venv = Join-Path $PSScriptRoot '.venv'
$python = Join-Path $venv 'Scripts/python.exe'
if (-not (Test-Path $python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv $venv }
    else { & python -m venv $venv }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $python -m pip install -r requirements.txt -r requirements-ui.txt -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $python cli.py init
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $python -m pytest -q
exit $LASTEXITCODE
