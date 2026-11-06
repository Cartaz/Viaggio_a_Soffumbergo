param(
 [string]$EngineRoot='C:\Program Files\Epic Games\UE_5.8',
 [ValidateSet('A','B')][string]$Preset='A',
 [int]$Width=3840,
 [int]$Height=2160
)
$ErrorActionPreference='Stop'
$labProject=Join-Path $PSScriptRoot 'Unreal\SoffumbergoLab.uproject'
$labEditor=Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
if(!(Test-Path -LiteralPath $labEditor)){throw 'Unreal Engine 5.8 installation not found.'}
if(!(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'Unreal\Content\Imported\YarisChaos1.uasset'))){
 throw 'Private imported Yaris asset missing. Follow README before launching.'
}
# Interactive game using the installed engine, not a standalone redistributed package.
& $labEditor $labProject /Game/Maps/Lab -game -windowed "-ResX=$Width" "-ResY=$Height" -ForceRes -NoVSync "-LabPreset=$Preset" "-ExecCmds=t.MaxFPS 60,r.SkyLight.RealTimeReflectionCapture 0" "-ini:GameUserSettings:[/Script/Engine.GameUserSettings]:FrameRateLimit=60" "-ini:Engine:[SystemSettings]:t.MaxFPS=60,[SystemSettings]:r.SkyLight.RealTimeReflectionCapture=0"
