param([string]$EngineRoot='C:\Program Files\Epic Games\UE_5.8')
$ErrorActionPreference='Stop'
$project=Join-Path $PSScriptRoot 'Unreal\SoffumbergoLab.uproject'
$version=Join-Path $EngineRoot 'Engine\Build\Build.version'
$build=Join-Path $EngineRoot 'Engine\Build\BatchFiles\Build.bat'
if (!(Test-Path -LiteralPath $version) -or !(Test-Path -LiteralPath $build)) {
 throw 'Unreal download/install incomplete: no compilation executed.'
}
$engineInfo=Get-Content -LiteralPath $version -Raw | ConvertFrom-Json
if($engineInfo.MajorVersion -ne 5 -or $engineInfo.MinorVersion -ne 8) {
 throw 'Expected exactly Unreal 5.8; refusing implicit version substitution.'
}
& $build SoffumbergoLabEditor Win64 Development "-Project=$project" -WaitMutex -NoHotReloadFromIDE
if($LASTEXITCODE -ne 0){throw "Unreal build failed ($LASTEXITCODE)"}
