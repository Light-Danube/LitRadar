$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$venv = Join-Path $PSScriptRoot '.venv'
$python = Join-Path $venv 'Scripts/python.exe'
$marker = Join-Path $venv '.litradar-deps-0.5.3'
if (-not (Test-Path $python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv $venv }
    else { & python -m venv $venv }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
if (-not (Test-Path $marker)) {
    & $python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m pip install -r requirements.txt -r requirements-ui.txt
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Set-Content -Path $marker -Value 'ready'
}
if ($args.Count -eq 0) { & $python cli.py ui }
else { & $python cli.py @args }
exit $LASTEXITCODE
