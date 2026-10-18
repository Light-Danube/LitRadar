$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$venv = Join-Path $PSScriptRoot '.venv'
$python = Join-Path $venv 'Scripts/python.exe'
$marker = Join-Path $venv '.litbeacon-deps-1.0.0-local'
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
if (-not (Test-Path $marker)) {
    & $python -m pip install '.[web,ui,annotations]'
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m pip check
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Set-Content -Path $marker -Value 'ready'
}
& $python cli.py init
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($args.Count -eq 0) { & $python cli.py ui }
else { & $python cli.py @args }
exit $LASTEXITCODE
