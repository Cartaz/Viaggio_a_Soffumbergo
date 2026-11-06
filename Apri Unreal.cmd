@echo off
set "UE_EDITOR=C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
if not exist "%UE_EDITOR%" (
 echo Unreal Engine 5.8 non trovato.
 pause
 exit /b 1
)
start "" "%UE_EDITOR%" "%~dp0Unreal\SoffumbergoLab.uproject" /Game/Maps/ValleLiDAR
