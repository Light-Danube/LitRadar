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
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 --version *> $null
        if ($LASTEXITCODE -eq 0) { & py -3.12 -m venv $venv }
        else { & py -3.11 -m venv $venv }
    } else { throw 'Install Python 3.12 or 3.11 with the Windows py launcher first.' }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& $python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'This .venv uses old Python. Install Python 3.12 and create a fresh .venv.' }
& $python -m pip install '.[web,ui,annotations]'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $python -m pip check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Get-ChildItem -Path $venv -Filter '.litradar-deps-*' -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Set-Content -Path (Join-Path $venv '.litbeacon-deps-1.0.0-local') -Value 'ready'
& $python cli.py init
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host 'LitBeacon checkout updated and runtime dependencies installed. Run development tests separately if needed.' -ForegroundColor Green
exit 0
