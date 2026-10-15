# Executes the real helper with fake cmdlets only; never accesses the OS scheduler.
param([switch]$Worker, [string]$Action = 'status', [string]$TaskSet = 'all',
      [string]$StatePath, [string]$TemporaryRoot, [string]$Fault = '', [string]$Time = '08:00')
$ErrorActionPreference = 'Stop'
$Target = Join-Path (Split-Path $PSScriptRoot -Parent) 'schedule_litradar.ps1'
if ($Worker) {
    $script:State = Get-Content -Raw -LiteralPath $StatePath | ConvertFrom-Json
    function Save-State { $script:State | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $StatePath -Encoding UTF8 }
    function Get-ScheduledTask {
        [CmdletBinding()]param($TaskName, $TaskPath)
        if ($Fault -eq 'query') { throw 'Synthetic query permission failure' }
        $Task = @($script:State.Tasks | Where-Object { $_.TaskName -eq $TaskName })
        if ($Task.Count -eq 0) {
            $Record = [System.Management.Automation.ErrorRecord]::new([Exception]::new('Synthetic missing task'), 'SyntheticMissing', [System.Management.Automation.ErrorCategory]::ObjectNotFound, $TaskName)
            $PSCmdlet.ThrowTerminatingError($Record)
        }
        return $Task[0]
    }
    function Get-ScheduledTaskInfo { [CmdletBinding()]param($TaskName, $TaskPath)
        if ($Fault -eq 'info') { throw 'Synthetic info permission failure' }
        return [pscustomobject]@{LastRunTime='synthetic'; NextRunTime='synthetic'; LastTaskResult=0}
    }
    function Unregister-ScheduledTask { [CmdletBinding(SupportsShouldProcess)]param($TaskName, $TaskPath)
        if ($Fault -eq 'remove') { throw 'Synthetic removal permission failure' }
        $script:State.Tasks = @($script:State.Tasks | Where-Object { $_.TaskName -ne $TaskName }); Save-State
    }
    function New-ScheduledTaskSettingsSet { param([switch]$StartWhenAvailable, $MultipleInstances, $ExecutionTimeLimit)
        return [pscustomobject]@{MultipleInstances=$MultipleInstances; StartWhenAvailable=[bool]$StartWhenAvailable}
    }
    function New-ScheduledTaskPrincipal { param($UserId, $LogonType, $RunLevel)
        return [pscustomobject]@{LogonType=$LogonType; RunLevel=$RunLevel}
    }
    function New-ScheduledTaskAction { param($Execute, $Argument, $WorkingDirectory)
        return [pscustomobject]@{Execute=$Execute; Arguments=$Argument; WorkingDirectory=$WorkingDirectory}
    }
    function New-ScheduledTaskTrigger { param([switch]$Weekly, [switch]$Daily, $DaysOfWeek, $At)
        return [pscustomobject]@{Weekly=[bool]$Weekly; Daily=[bool]$Daily}
    }
    function Register-ScheduledTask { [CmdletBinding()]param($TaskName, $TaskPath, $Action, $Trigger, $Settings, $Principal, $Description, [switch]$Force)
        if ($Fault -eq 'install') { throw 'Synthetic registration permission failure' }
        if (-not $Force) { throw 'Repeated installation must replace the same task' }
        $script:State.Tasks = @($script:State.Tasks | Where-Object { $_.TaskName -ne $TaskName }) + @([pscustomobject]@{
            TaskName=$TaskName; State='Ready'; Action=$Action; Settings=$Settings; Principal=$Principal; Trigger=$Trigger
        }); Save-State
    }
    & $Target -Action $Action -TaskSet $TaskSet -Time $Time -PythonPath (Get-Process -Id $PID).Path `
        -ConfigPath (Join-Path $TemporaryRoot 'custom settings.json') -DatabasePath (Join-Path $TemporaryRoot 'custom database.sqlite3') `
        -ProfilePath (Join-Path $TemporaryRoot 'custom profile.json') -WorkspaceRoot $TemporaryRoot
    exit $LASTEXITCODE
}
$Root = Join-Path ([IO.Path]::GetTempPath()) ('litbeacon-fake-scheduler-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $Root | Out-Null
$State = Join-Path $Root 'tasks.json'
'{"Tasks":[]}' | Set-Content -LiteralPath $State -Encoding UTF8
$HostExecutable = (Get-Process -Id $PID).Path
$HarnessPath = $PSCommandPath
function Invoke-Helper($Action, $TaskSet, $Fault = '', $Expected = 0, $SelectedTime = '08:00') {
    $OldPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $WorkerArguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $HarnessPath, '-Worker', '-Action', $Action,
                             '-TaskSet', $TaskSet, '-StatePath', $State, '-TemporaryRoot', $Root, '-Time', $SelectedTime)
        if ($Fault) { $WorkerArguments += @('-Fault', $Fault) }
        $Output = & $HostExecutable @WorkerArguments 2>&1
        $ResultCode = $LASTEXITCODE
    } finally { $ErrorActionPreference = $OldPreference }
    if (($Expected -eq 0 -and $ResultCode -ne 0) -or ($Expected -ne 0 -and $ResultCode -eq 0)) {
        throw "Unexpected helper result for $Action/$TaskSet/$Fault : $Output"
    }
    return $Output
}
function Tasks { return @((Get-Content -Raw -LiteralPath $State | ConvertFrom-Json).Tasks) }
try {
    $Status = Invoke-Helper 'status' 'all'
    if (($Status -join ' ') -notmatch 'not installed') { throw 'Missing task status failed' }
    $null = Invoke-Helper 'install' 'scan'
    $null = Invoke-Helper 'install' 'digest'
    $null = Invoke-Helper 'install' 'all'
    $Tasks = Tasks
    if ($Tasks.Count -ne 2) { throw 'Repeated install created duplicate tasks' }
    foreach ($Task in $Tasks) {
        if ($Task.Settings.MultipleInstances -ne 'IgnoreNew' -or $Task.Principal.LogonType -ne 'Interactive') { throw 'Unsafe task settings' }
        foreach ($PathValue in @('custom settings.json', 'custom database.sqlite3', 'custom profile.json')) {
            if (-not $Task.Action.Arguments.Contains('"' + (Join-Path $Root $PathValue) + '"')) { throw 'Selected path not quoted in task action' }
        }
    }
    $null = Invoke-Helper 'status' 'scan'
    $null = Invoke-Helper 'status' 'digest'
    $null = Invoke-Helper 'status' 'all'
    $Before = Get-Content -Raw -LiteralPath $State
    $null = Invoke-Helper 'remove' 'scan' 'remove' 1
    if ((Get-Content -Raw -LiteralPath $State) -ne $Before) { throw 'Failed removal changed task state' }
    $null = Invoke-Helper 'status' 'all' 'query' 1
    $null = Invoke-Helper 'status' 'all' 'info' 1
    $null = Invoke-Helper 'install' 'scan' 'install' 1
    $null = Invoke-Helper 'install' 'scan' '' 1 'invalid-time'
    $null = Invoke-Helper 'remove' 'scan'
    if ((Tasks).Count -ne 1 -or (Tasks)[0].TaskName -ne 'LitRadar-Digest') { throw 'Per-job removal affected the other task' }
    $null = Invoke-Helper 'remove' 'scan'
    $null = Invoke-Helper 'remove' 'all'
    if ((Tasks).Count -ne 0) { throw 'Remove all left tasks behind' }
    Write-Output 'Actual scheduler helper passed isolated fake-cmdlet lifecycle/failure checks; no OS tasks accessed.'
} finally { Remove-Item -LiteralPath $Root -Recurse -Force }
