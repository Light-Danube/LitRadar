$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host 'LitBeacon updater — Git checkout mode' -ForegroundColor Cyan
if (-not (Test-Path (Join-Path $PSScriptRoot '.git'))) {
    Write-Host ''
    Write-Host 'Update not started: this folder has no .git directory.' -ForegroundColor Red
    Write-Host 'It looks like LitBeacon (formerly LitRadar) was installed by copying files from a ZIP archive.' -ForegroundColor Yellow
    Write-Host 'This updater can pull source updates only for a Git checkout; it did not change any files.'
    Write-Host 'For a ZIP install, apply the next released patch/full ZIP manually. To enable this updater, clone the repository with GitHub Desktop.'
    exit 2
}
Write-Host 'Checking local changes before pulling...' -ForegroundColor Cyan
$dirty = git status --porcelain
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($dirty) {
    Write-Host 'Update stopped: there are local tracked changes.' -ForegroundColor Yellow
    Write-Host 'Commit or stash them in GitHub Desktop, then run this script again.'
    Write-Host 'Local database, offline files, source cache, and .env are ignored and are not the cause of this check.'
    exit 3
}
git pull --ff-only
if ($LASTEXITCODE -ne 0) {
    Write-Host 'git pull failed. Check the message above and your network/repository state.' -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host 'Source files updated. Preparing environment...' -ForegroundColor Green
$venv = Join-Path $PSScriptRoot '.venv'
$python = Join-Path $venv 'Scripts/python.exe'
if (-not (Test-Path $python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv $venv }
    else { & python -m venv $venv }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $python -m pip install -r requirements.txt -r requirements-ui.txt -r requirements-dev.txt -r requirements-llm.txt -r requirements-web.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Get-ChildItem -Path $venv -Filter '.litradar-deps-*' -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Set-Content -Path (Join-Path $venv '.litbeacon-deps-1.0.0-full') -Value 'ready'
& $python cli.py init
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Tests failed. LitBeacon was updated, but the installation is not verified.' -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host 'LitBeacon update verified: dependencies installed and tests passed.' -ForegroundColor Green
exit 0
