param(
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [datetime]$StartTime = [datetime]'2026-10-24T22:45:00',
    [datetime]$EndTime = [datetime]'2026-10-24T23:15:00'
)
# Read-only system queries. New local evidence files only; no stress, reboot or settings changes.
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Preserve existing evidence directory' }
$out = New-Item -ItemType Directory -Path $OutputDirectory
$queries = [System.Collections.Generic.List[object]]::new()
function Read-Events([string]$LogName, [datetime]$From, [datetime]$Until, [string]$Name) {
    $rows = @()
    $failure = $null
    try { $rows = @(Get-WinEvent -FilterHashtable @{LogName=$LogName;StartTime=$From;EndTime=$Until} -ErrorAction Stop) }
    catch { if ($_.FullyQualifiedErrorId -notmatch '^NoMatchingEventsFound') { $failure = $_.Exception.Message } }
    $queries.Add([pscustomobject]@{name=$Name;log=$LogName;start=$From.ToString('o');end=$Until.ToString('o');count=$rows.Count;error=$failure})
    $summary = @($rows | Sort-Object TimeCreated | ForEach-Object {
        [pscustomobject]@{time_local=$_.TimeCreated.ToString('o');record_id=$_.RecordId;id=$_.Id;provider=$_.ProviderName;level=$_.Level;message=$_.Message}
    })
    ConvertTo-Json -InputObject $summary -Depth 5 | Set-Content -LiteralPath (Join-Path $out.FullName ($Name+'.json')) -Encoding utf8
    $xml = "<Events>`n" + (($rows | ForEach-Object {$_.ToXml()}) -join "`n") + "`n</Events>"
    $xml | Set-Content -LiteralPath (Join-Path $out.FullName ($Name+'.xml')) -Encoding utf8
}
Read-Events 'System' $StartTime $EndTime 'system_window'
Read-Events 'Application' $StartTime $EndTime 'application_window'
Read-Events 'Microsoft-Windows-Kernel-Power/Thermal-Operational' $StartTime $EndTime 'thermal_window'
Read-Events 'Microsoft-Windows-Resource-Exhaustion-Detector/Operational' $StartTime $EndTime 'resource_window'
$system = [ordered]@{
    collected_at=(Get-Date).ToString('o')
    os=Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,LastBootUpTime,FreePhysicalMemory
    computer=Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,TotalPhysicalMemory
    cpu=Get-CimInstance Win32_Processor | Select-Object Name
    gpu=Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,DriverDate,PNPDeviceID
    bios=Get-CimInstance Win32_BIOS | Select-Object Manufacturer,SMBIOSBIOSVersion,ReleaseDate
    board=Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer,Product
    pagefile=Get-CimInstance Win32_PageFileUsage | Select-Object Name,AllocatedBaseSize,CurrentUsage,PeakUsage
    crash_control=Get-ItemProperty 'HKLM:/SYSTEM/CurrentControlSet/Control/CrashControl' | Select-Object CrashDumpEnabled,LogEvent,AutoReboot,DumpFile,MinidumpDir
    native_processes=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'UnrealEditor|ShaderCompileWorker'} | Select-Object Name,ProcessId,CommandLine)
}
try { $system['acpi_temperature'] = @(Get-CimInstance -Namespace root/WMI -ClassName MSAcpi_ThermalZoneTemperature) }
catch { $system['acpi_temperature_unavailable'] = $_.Exception.Message }
$dumps = @()
foreach($directory in @('C:/Windows/LiveKernelReports','C:/Windows/Minidump')) {
    try {
        if (Test-Path -LiteralPath $directory) {
            $dumps += @(Get-ChildItem -LiteralPath $directory -Recurse -File | Select-Object FullName,Length,LastWriteTime)
        }
    } catch { $system[$directory+'_query_error'] = $_.Exception.Message }
}
if (Test-Path -LiteralPath 'C:/Windows/MEMORY.DMP') { $dumps += Get-Item -LiteralPath 'C:/Windows/MEMORY.DMP' | Select-Object FullName,Length,LastWriteTime }
$system['dumps'] = $dumps
$system['event_queries'] = @($queries.ToArray())
$system | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $out.FullName 'system_snapshot.json') -Encoding utf8
Write-Output ('SHUTDOWN_EVIDENCE_SAVED '+$out.FullName)
