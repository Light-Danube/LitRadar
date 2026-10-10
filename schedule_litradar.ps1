param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('install', 'remove', 'status')]
    [string]$Action,
    [ValidateSet('scan', 'digest', 'all')]
    [string]$TaskSet = 'all',
    [ValidateSet('daily', 'weekly')]
    [string]$Frequency = 'daily',
    [string]$Time = '08:00'
)

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$TaskNames = @{
    scan = 'LitRadar-Scan'
    digest = 'LitRadar-Digest'
}
$Selected = if ($TaskSet -eq 'all') { @('scan', 'digest') } else { @($TaskSet) }

try {
    $At = [datetime]::ParseExact($Time, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture)
} catch {
    Write-Error "Invalid time '$Time'. Use local 24-hour HH:mm, e.g. 08:00."
    exit 2
}

if ($Action -eq 'status') {
    foreach ($Job in $Selected) {
        $Name = $TaskNames[$Job]
        $Task = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
        if ($null -eq $Task) {
            Write-Output "$Name : not installed"
        } else {
            $Info = Get-ScheduledTaskInfo -TaskName $Name
            Write-Output ("{0} : state={1}; last={2}; next={3}; last-result={4}" -f $Name, $Task.State, $Info.LastRunTime, $Info.NextRunTime, $Info.LastTaskResult)
        }
    }
    exit 0
}

if ($Action -eq 'remove') {
    foreach ($Job in $Selected) {
        $Name = $TaskNames[$Job]
        Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction SilentlyContinue
        Write-Output "Removed (if it existed): $Name"
    }
    exit 0
}

$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) {
    Write-Error "Project virtual environment not found. Run run_litradar.bat once first so LitRadar creates .venv and installs dependencies."
    exit 2
}
$Cli = Join-Path $Root 'cli.py'
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

foreach ($Job in $Selected) {
    $Name = $TaskNames[$Job]
    $Period = if ($Job -eq 'scan') { $Frequency } else { $Frequency }
    $Arguments = ('"{0}" scheduled-run --job {1} --period {2}' -f $Cli, $Job, $Period)
    $TaskAction = New-ScheduledTaskAction -Execute $Python -Argument $Arguments -WorkingDirectory $Root
    if ($Frequency -eq 'weekly') {
        $Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $At
    } else {
        $Trigger = New-ScheduledTaskTrigger -Daily -At $At
    }
    Register-ScheduledTask -TaskName $Name -Action $TaskAction -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "LitRadar v0.7 scheduled $Job; runs only under the current user's interactive session and logs to $Root\logs." -Force | Out-Null
    Write-Output "Installed $Name ($Frequency at $Time local time)."
}
Write-Output "Tasks start when available if a scheduled time is missed, but the computer must be on and the user logged in. Check with: python cli.py schedule status --job all"
