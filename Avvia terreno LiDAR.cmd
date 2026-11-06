@echo off
set "LIDAR_PACKAGE=%~dp0build\Windows\SoffumbergoLab.exe"
if exist "%LIDAR_PACKAGE%" (
 start "" "%LIDAR_PACKAGE%" -windowed -ResX=3840 -ResY=2160 -ForceRes -LabPreset=C -ExecCmds="t.MaxFPS 60,r.SkyLight.RealTimeReflectionCapture 0" -ini:GameUserSettings:[/Script/Engine.GameUserSettings]:FrameRateLimit=60 -ini:Engine:[SystemSettings]:t.MaxFPS=60,[SystemSettings]:r.SkyLight.RealTimeReflectionCapture=0
 exit /b 0
)
set "LIDAR_EDITOR=C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
if not exist "%LIDAR_EDITOR%" (
 echo Unreal Engine 5.8 e pacchetto Windows non trovati.
 pause
 exit /b 1
)
start "" "%LIDAR_EDITOR%" "%~dp0Unreal\SoffumbergoLab.uproject" /Game/Maps/ValleLiDAR -game -windowed -ResX=3840 -ResY=2160 -ForceRes -LabPreset=C -ExecCmds="t.MaxFPS 60,r.SkyLight.RealTimeReflectionCapture 0" -ini:GameUserSettings:[/Script/Engine.GameUserSettings]:FrameRateLimit=60 -ini:Engine:[SystemSettings]:t.MaxFPS=60,[SystemSettings]:r.SkyLight.RealTimeReflectionCapture=0
