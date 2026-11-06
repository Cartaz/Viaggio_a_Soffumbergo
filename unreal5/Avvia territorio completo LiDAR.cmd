@echo off
set "CIRCUIT_PACKAGE=%~dp0build\CircuitWindows\Windows\SoffumbergoLab.exe"
if exist "%CIRCUIT_PACKAGE%" (
 start "" "%CIRCUIT_PACKAGE%" /Game/Maps/CircuitoSoffumbergo -windowed -ResX=3840 -ResY=2160 -ForceRes -LabPreset=C -ExecCmds="t.MaxFPS 60,r.SkyLight.RealTimeReflectionCapture 0" -ini:GameUserSettings:[/Script/Engine.GameUserSettings]:FrameRateLimit=60 -ini:Engine:[SystemSettings]:t.MaxFPS=60,[SystemSettings]:r.SkyLight.RealTimeReflectionCapture=0
 exit /b 0
)
set "CIRCUIT_EDITOR=C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
if not exist "%CIRCUIT_EDITOR%" (
 echo Unreal Engine 5.8 e pacchetto del territorio non trovati.
 pause
 exit /b 1
)
start "" "%CIRCUIT_EDITOR%" "%~dp0Unreal\SoffumbergoLab.uproject" /Game/Maps/CircuitoSoffumbergo -game -windowed -ResX=3840 -ResY=2160 -ForceRes -LabPreset=C -ExecCmds="t.MaxFPS 60,r.SkyLight.RealTimeReflectionCapture 0" -ini:GameUserSettings:[/Script/Engine.GameUserSettings]:FrameRateLimit=60 -ini:Engine:[SystemSettings]:t.MaxFPS=60,[SystemSettings]:r.SkyLight.RealTimeReflectionCapture=0
