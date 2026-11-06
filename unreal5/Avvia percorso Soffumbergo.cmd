@echo off
set "DRIVING_PACKAGE=%~dp0build\DrivingWindows\Windows\SoffumbergoLab.exe"
if exist "%DRIVING_PACKAGE%" (
 start "" "%DRIVING_PACKAGE%" /Game/Maps/CircuitoGuidabile -windowed -ResX=3840 -ResY=2160 -ForceRes -LabPreset=C -ExecCmds="t.MaxFPS 60,r.SkyLight.RealTimeReflectionCapture 0" -ini:GameUserSettings:[/Script/Engine.GameUserSettings]:FrameRateLimit=60 -ini:Engine:[SystemSettings]:t.MaxFPS=60,[SystemSettings]:r.SkyLight.RealTimeReflectionCapture=0
 exit /b 0
)
set "DRIVING_EDITOR=C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
if not exist "%DRIVING_EDITOR%" (
 echo Unreal Engine 5.8 e pacchetto del percorso non trovati.
 pause
 exit /b 1
)
start "" "%DRIVING_EDITOR%" "%~dp0Unreal\SoffumbergoLab.uproject" /Game/Maps/CircuitoGuidabile -game -windowed -ResX=3840 -ResY=2160 -ForceRes -LabPreset=C -ExecCmds="t.MaxFPS 60,r.SkyLight.RealTimeReflectionCapture 0" -ini:GameUserSettings:[/Script/Engine.GameUserSettings]:FrameRateLimit=60 -ini:Engine:[SystemSettings]:t.MaxFPS=60,[SystemSettings]:r.SkyLight.RealTimeReflectionCapture=0
