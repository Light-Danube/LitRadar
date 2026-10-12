$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$venv = Join-Path $PSScriptRoot '.venv'
$python = Join-Path $venv 'Scripts/python.exe'
$marker = Join-Path $venv '.litbeacon-deps-0.8.0-full'
if (-not (Test-Path $python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv $venv }
    else { & python -m venv $venv }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
if (-not (Test-Path $marker)) {
    & $python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m pip install -r requirements.txt -r requirements-ui.txt -r requirements-dev.txt -r requirements-llm.txt -r requirements-web.txt
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Set-Content -Path $marker -Value 'ready'
}
& $python cli.py init
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($args.Count -eq 0) { & $python cli.py ui }
else { & $python cli.py @args }
exit $LASTEXITCODE
