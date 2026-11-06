param([string]$EngineRoot='C:\Program Files\Epic Games\UE_5.8',[switch]$Circuit,[switch]$Driving)
$ErrorActionPreference='Stop'
if($Circuit -and $Driving){throw 'Scegliere Circuit oppure Driving.'}
$terrainProject=Join-Path $PSScriptRoot 'Unreal\SoffumbergoLab.uproject'
$terrainArchive=Join-Path $PSScriptRoot $(if($Driving){'build\DrivingWindows'}elseif($Circuit){'build\CircuitWindows'}else{'build'})
$terrainPackage=Join-Path $terrainArchive 'Windows'
$terrainMap=if($Driving){'/Game/Maps/CircuitoGuidabile'}elseif($Circuit){'/Game/Maps/CircuitoSoffumbergo'}else{'/Game/Maps/ValleLiDAR'}
$terrainCookMaps=$terrainMap
$terrainBuildId=$null
if($Driving){
 $terrainRuntimePath=Join-Path $PSScriptRoot 'Unreal\Content\Data\circuit_driving_world.json'
 $terrainManifest=Get-Content -LiteralPath $terrainRuntimePath -Raw | ConvertFrom-Json
 $terrainCurrent=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'parameters\current_road_design.json') -Raw | ConvertFrom-Json
 $terrainImport=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'results\current_road_import.json') -Raw | ConvertFrom-Json
 if($terrainManifest.build_id -ne $terrainCurrent.build_id -or $terrainManifest.build_id -ne $terrainImport.build_id){throw 'Importare prima la generazione stradale corrente.'}
 if(@($terrainManifest.tiles).Count -ne 113){throw 'Elenco dei 113 settori stradali incompleto.'}
 $terrainBuildId=$terrainManifest.build_id
 $terrainCookMaps=(@($terrainMap)+@($terrainManifest.tiles | ForEach-Object {$_.map})) -join '+'
}elseif($Circuit){
 $terrainManifest=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'terrain\world_tiles\manifest.json') -Raw | ConvertFrom-Json
 if(-not $terrainManifest.native_import_verified){throw 'Settori nativi non verificati.'}
 # UAT -map overrides the editor MapsToCook list. These maps are referenced
 # by runtime JSON strings, so every geographic level must be explicit here.
 $terrainCookMaps=(@($terrainMap)+@($terrainManifest.tiles | ForEach-Object {$_.map})) -join '+'
}
$terrainUat=Join-Path $EngineRoot 'Engine\Build\BatchFiles\RunUAT.bat'
$terrainVersion=Get-Content -LiteralPath (Join-Path $EngineRoot 'Engine\Build\Build.version') -Raw | ConvertFrom-Json
if($terrainVersion.MajorVersion -ne 5 -or $terrainVersion.MinorVersion -ne 8){throw 'Richiesto Unreal Engine 5.8.'}
$terrainArguments=@('BuildCookRun',"-project=$terrainProject",'-noP4','-platform=Win64',
 '-target=SoffumbergoLab','-clientconfig=Development','-build','-cook','-stage','-pak',
 '-archive',"-archivedirectory=$terrainArchive",'-unattended','-utf8output','-nocompileeditor','-nodebuginfo',
 "-map=$terrainCookMaps")
$terrainTimer=[Diagnostics.Stopwatch]::StartNew()
& $terrainUat @terrainArguments
$terrainExit=$LASTEXITCODE
$terrainTimer.Stop()
$terrainExecutables=@(Get-ChildItem -LiteralPath $terrainPackage -Recurse -Filter 'SoffumbergoLab.exe' -File -ErrorAction SilentlyContinue | ForEach-Object {$_.FullName})
@{exit_code=$terrainExit;wall_s=$terrainTimer.Elapsed.TotalSeconds;executables=$terrainExecutables;
 map=$terrainMap;build_id=$terrainBuildId;cooked_maps=$terrainCookMaps.Split('+');scope='local Windows Development package; runtime verification required'} |
 ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot $(if($Driving){'results\driving_windows_packaging.json'}elseif($Circuit){'results\circuit_windows_packaging.json'}else{'results\lidar_windows_packaging.json'})) -Encoding utf8
if($terrainExit -ne 0 -or $terrainExecutables.Count -eq 0){throw "Packaging Windows non completato ($terrainExit)"}
