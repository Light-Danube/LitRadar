param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('install', 'remove', 'status')]
    [string]$Action,
    [ValidateSet('scan', 'digest', 'all')]
    [string]$TaskSet = 'all',
    [ValidateSet('daily', 'weekly')]
    [string]$Frequency = 'daily',
    [string]$Time = '08:00',
    [string]$ConfigPath,
    [string]$DatabasePath,
    [string]$ProfilePath,
    [string]$PythonPath,
    [string]$WorkspaceRoot
)

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$TaskNames = @{ scan = 'LitRadar-Scan'; digest = 'LitRadar-Digest' }
$Selected = if ($TaskSet -eq 'all') { @('scan', 'digest') } else { @($TaskSet) }

function Find-LitRadarTask([string]$Name) {
    try {
        return Get-ScheduledTask -TaskName $Name -TaskPath '\' -ErrorAction Stop
    } catch {
        if ($_.CategoryInfo.Category -eq [System.Management.Automation.ErrorCategory]::ObjectNotFound) { return $null }
        throw
    }
}

try {
    if ($Action -eq 'status') {
        foreach ($Job in $Selected) {
            $Name = $TaskNames[$Job]
            $Task = Find-LitRadarTask $Name
            if ($null -eq $Task) { Write-Output "$Name : not installed" } else {
                $Info = Get-ScheduledTaskInfo -TaskName $Name -TaskPath '\' -ErrorAction Stop
                Write-Output ("{0} : state={1}; last={2}; next={3}; last-result={4}" -f $Name, $Task.State, $Info.LastRunTime, $Info.NextRunTime, $Info.LastTaskResult)
            }
        }
        exit 0
    }
    if ($Action -eq 'remove') {
        foreach ($Job in $Selected) {
            $Name = $TaskNames[$Job]
            if ($null -ne (Find-LitRadarTask $Name)) {
                Unregister-ScheduledTask -TaskName $Name -TaskPath '\' -Confirm:$false -ErrorAction Stop
            }
            Write-Output "Removed (if it existed): $Name"
        }
        exit 0
    }
    $At = [datetime]::ParseExact($Time, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture)
    if (-not $PythonPath) { $PythonPath = Join-Path $Root '.venv\Scripts\python.exe' }
    if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) { throw 'Python environment is missing' }
    if (-not $WorkspaceRoot) { $WorkspaceRoot = $Root }
    if (-not $ConfigPath) { $ConfigPath = Join-Path $Root 'digest_config.json' }
    if (-not $DatabasePath) { $DatabasePath = Join-Path $Root 'data\litradar.sqlite3' }
    if (-not $ProfilePath) { $ProfilePath = Join-Path $Root 'research_profile.json' }
    $Cli = Join-Path $Root 'cli.py'
    foreach ($PathValue in @($Cli, $DatabasePath, $ConfigPath, $ProfilePath, $PythonPath, $WorkspaceRoot)) {
        if ($PathValue.Contains('"')) { throw 'Invalid quoted path' }
    }
    $Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2)
    $Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
    foreach ($Job in $Selected) {
        $Name = $TaskNames[$Job]
        $Arguments = ('"{0}" --db "{1}" scheduled-run --job {2} --period {3} --config "{4}" --profile "{5}"' -f $Cli, $DatabasePath, $Job, $Frequency, $ConfigPath, $ProfilePath)
        $TaskAction = New-ScheduledTaskAction -Execute $PythonPath -Argument $Arguments -WorkingDirectory $WorkspaceRoot
        if ($Frequency -eq 'weekly') {
            $Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $At
        } else { $Trigger = New-ScheduledTaskTrigger -Daily -At $At }
        Register-ScheduledTask -TaskName $Name -TaskPath '\' -Action $TaskAction -Trigger $Trigger -Settings $Settings -Principal $Principal -Description 'LitBeacon scheduled job; local interactive user; diagnostics under the LitBeacon log/ directory.' -Force -ErrorAction Stop | Out-Null
        Write-Output "Installed $Name ($Frequency at $Time local time)."
    }
    Write-Output 'Tasks start when available; the computer must be on and the user logged in. Check with: python cli.py schedule status --job all'
} catch {
    [Console]::Error.WriteLine('Task Scheduler action failed. Check task access, Python environment, paths and local HH:mm time; private error details are omitted.')
    exit 1
}
