$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& (Join-Path $PSScriptRoot 'setup_litbeacon.bat')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$venv = Join-Path $PSScriptRoot '.venv'
$python = Join-Path $venv 'Scripts/python.exe'
if ($args.Count -eq 0) { & $python cli.py ui }
else { & $python cli.py @args }
exit $LASTEXITCODE
