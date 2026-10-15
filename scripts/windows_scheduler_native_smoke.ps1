# Native Task Scheduler registration check, restricted to ephemeral GitHub-hosted CI.
param([string]$PythonPath = (Get-Command python -ErrorAction Stop).Source)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
    throw 'Native scheduler smoke is restricted to ephemeral GitHub-hosted CI.'
}
$Prefix = 'LitBeacon-CI-' + [guid]::NewGuid().ToString('N')
$Root = Join-Path ([IO.Path]::GetTempPath()) $Prefix
$Names = @("${Prefix}-Scan", "${Prefix}-Digest")
New-Item -ItemType Directory -Path $Root | Out-Null
$Source = Join-Path (Split-Path $PSScriptRoot -Parent) 'schedule_litradar.ps1'
$Helper = Join-Path $Root 'schedule_litradar.ps1'
$Text = [IO.File]::ReadAllText($Source)
foreach ($Literal in @("'LitRadar-Scan'", "'LitRadar-Digest'")) {
    if ([regex]::Matches($Text, [regex]::Escape($Literal)).Count -ne 1) { throw 'Unexpected task-name definitions; refusing native smoke.' }
}
# Only replace the two name literals; all production action/settings/lifecycle logic is unchanged.
$Text = $Text.Replace("'LitRadar-Scan'", "'$($Names[0])'").Replace("'LitRadar-Digest'", "'$($Names[1])'")
[IO.File]::WriteAllText($Helper, $Text)
[IO.File]::WriteAllText((Join-Path $Root 'cli.py'), 'print("Synthetic CI scheduler noop; no network or database")')
$HostExecutable = (Get-Process -Id $PID).Path
$At = (Get-Date).AddHours(2).ToString('HH:mm')
function Invoke-NativeHelper($Action, $TaskSet) {
    & $HostExecutable -NoProfile -ExecutionPolicy Bypass -File $Helper -Action $Action -TaskSet $TaskSet -Time $At `
        -PythonPath $PythonPath -ConfigPath (Join-Path $Root 'settings.json') -DatabasePath (Join-Path $Root 'synthetic.sqlite3') `
        -ProfilePath (Join-Path $Root 'profile.json') -WorkspaceRoot $Root
    if ($LASTEXITCODE -ne 0) { throw "Native isolated scheduler action failed: $Action/$TaskSet" }
}
try {
    Invoke-NativeHelper 'install' 'scan'
    $null = Disable-ScheduledTask -TaskName $Names[0] -TaskPath '\' -ErrorAction Stop
    Invoke-NativeHelper 'install' 'digest'
    $null = Disable-ScheduledTask -TaskName $Names[1] -TaskPath '\' -ErrorAction Stop
    Invoke-NativeHelper 'install' 'all'
    foreach ($Name in $Names) {
        $null = Disable-ScheduledTask -TaskName $Name -TaskPath '\' -ErrorAction Stop
        $Tasks = @(Get-ScheduledTask -TaskName $Name -TaskPath '\' -ErrorAction Stop)
        if ($Tasks.Count -ne 1 -or [string]$Tasks[0].Settings.MultipleInstances -notin @('IgnoreNew', '2')) { throw 'Native task identity/settings verification failed' }
        if (-not $Tasks[0].Actions[0].Arguments.Contains('"' + (Join-Path $Root 'settings.json') + '"')) { throw 'Custom configuration missing from native action' }
    }
    Invoke-NativeHelper 'status' 'scan'
    Invoke-NativeHelper 'status' 'digest'
    Invoke-NativeHelper 'status' 'all'
    Invoke-NativeHelper 'remove' 'scan'
    if (@(Get-ScheduledTask -TaskName $Names[1] -TaskPath '\' -ErrorAction Stop).Count -ne 1) { throw 'Scan removal changed digest task' }
    Invoke-NativeHelper 'remove' 'scan'
    Invoke-NativeHelper 'remove' 'all'
    Invoke-NativeHelper 'status' 'all'
    Write-Output 'Native Windows Scheduler unique-task install/reinstall/status/remove passed; task execution, personal/default tasks and live services were not tested.'
} finally {
    $CleanupFailed = $false
    foreach ($Name in $Names) {
        try {
            # Query and delete only these generated names. Missing tasks are expected after removal.
            $Task = Get-ScheduledTask -TaskName $Name -TaskPath '\' -ErrorAction Stop
            if ($null -ne $Task) { Unregister-ScheduledTask -TaskName $Name -TaskPath '\' -Confirm:$false -ErrorAction Stop }
        } catch {
            if ($_.CategoryInfo.Category -ne [System.Management.Automation.ErrorCategory]::ObjectNotFound) { $CleanupFailed = $true }
        }
    }
    Remove-Item -LiteralPath $Root -Recurse -Force
    if ($CleanupFailed) { throw 'Could not remove a generated CI-only task; inspect the ephemeral runner logs.' }
}
