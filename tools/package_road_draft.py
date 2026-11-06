"""Export a physically verified road candidate without replacing the live build."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import _winapi

ROOT=Path(__file__).resolve().parents[1]
ENGINE=Path('C:/Program Files/Epic Games/UE_5.8')


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--draft',type=Path,required=True)
    p.add_argument('--lap-report',type=Path,required=True);p.add_argument('--surface-report',type=Path,required=True)
    p.add_argument('--background-log',type=Path)
    p.add_argument('--revision',help='Named runtime revision, preserving the first export of this terrain')
    p.add_argument('--attempt',default='v1',help='Separate export workspace/archive/logs; earlier attempts remain intact')
    args=p.parse_args()
    if not re.fullmatch('v[1-9][0-9]*',args.attempt):raise ValueError('Invalid export attempt')
    if args.background_log:sys.stdout=args.background_log.open('w',buffering=1);sys.stderr=sys.stdout
    draft=args.draft.resolve();world=draft/'circuit_driving_world.json';itinerary=draft/'circuit_itinerary.json'
    data=json.loads(world.read_text());build=data['build_id']
    preparation=draft/'structure_preparation.json'
    if preparation.exists() and json.loads(preparation.read_text()).get('diagnostic_only'):
        raise RuntimeError('A local diagnostic cannot be exported as a whole-territory candidate')
    if not re.fullmatch('[0-9a-f]{12}',build):raise ValueError('Invalid candidate id')
    lap=json.loads(args.lap_report.read_text());surface=json.loads(args.surface_report.read_text())
    if not lap['full_lap_passed'] or not surface['passed'] or lap['build_id']!=build or surface['build_id']!=build:
        raise RuntimeError('Native complete lap and full surface survey are required for this exact candidate')
    launch=json.loads((args.lap_report.parent/'launch_manifest.json').read_text())
    if launch['world_sha1']!=hashlib.sha1(world.read_bytes()).hexdigest() or launch['itinerary_sha1']!=hashlib.sha1(itinerary.read_bytes()).hexdigest():
        raise RuntimeError('Candidate data changed after the physical lap')
    if launch['native_binary_sha256']!=sha(ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoLab.dll'):
        raise RuntimeError('Native driving code changed after the accepted Editor lap')
    protected=[ROOT/'parameters/current_road_design.json',ROOT/'results/current_road_import.json',
               ROOT/'Unreal/Content/Data/circuit_driving_world.json',ROOT/'Unreal/Content/Data/circuit_itinerary.json',
               ROOT/'Unreal/Content/Maps/CircuitoGuidabile.umap',
               ROOT/'build/DrivingWindows/Windows/SoffumbergoLab/Content/Paks/SoffumbergoLab-Windows.pak']
    before={str(path):sha(path) for path in protected}
    revision=None
    if args.revision:
        if not re.fullmatch('[a-z][a-z0-9_]{0,31}',args.revision):raise ValueError('Invalid runtime revision')
        revision=json.loads((draft/'runtime_revision.json').read_text(encoding='utf-8'))
        if revision['revision']!=args.revision or revision['build_id']!=build:
            raise RuntimeError('Runtime revision does not match the selected draft')
        base=Path(revision['base_draft'])
        if any(sha(base/path.name)!=sha(path) for path in [world,itinerary]):
            raise RuntimeError('Runtime-only revision changed terrain or itinerary data')
        if any(sha(path)!=value for path,value in revision['source_sha256'].items()):
            raise RuntimeError('Runtime source changed after revision preparation')
    suffix='' if args.attempt=='v1' else '_'+args.attempt
    project=ROOT/'build'/('Q'+build+('_'+args.revision if args.revision else '')+suffix)
    archive=ROOT/'build/RoadCandidateWindows'/build
    if args.revision:archive=archive/args.revision
    if args.attempt!='v1':archive=archive/args.attempt
    if project.exists() or archive.exists():raise RuntimeError('Preserve previous candidate export; use its recorded result')
    project.mkdir(parents=True)
    original=ROOT/'Unreal';shutil.copyfile(original/'SoffumbergoLab.uproject',project/'SoffumbergoLab.uproject')
    shutil.copytree(original/'Config',project/'Config');shutil.copytree(original/'Source',project/'Source')
    shutil.copytree(original/'Binaries',project/'Binaries',ignore=shutil.ignore_patterns('*.pdb'))
    (project/'Content').mkdir()
    for item in (original/'Content').iterdir():
        if item.name=='Data':shutil.copytree(item,project/'Content/Data')
        elif item.is_dir():_winapi.CreateJunction(str(item),str(project/'Content'/item.name))
        elif item.is_file():shutil.copyfile(item,project/'Content'/item.name)
    for path in [world,itinerary]:shutil.copyfile(path,project/'Content/Data'/path.name)
    # A normal double click of this separate candidate opens its driving map.
    config=project/'Config/DefaultEngine.ini'
    text=config.read_text().replace('GameDefaultMap=/Game/Maps/ValleLiDAR','GameDefaultMap=/Game/Maps/CircuitoGuidabile')
    config.write_text(text)
    maps=['/Game/Maps/CircuitoGuidabile']+[tile['map'] for tile in data['tiles']]
    distant_maps=[tile['distant_map'] for tile in data['tiles'] if tile.get('distant_map')]
    if distant_maps:
        if len(distant_maps)!=113 or len(set(distant_maps))!=113 or not all(v.startswith('/Game/World/Distant/') for v in distant_maps):
            raise RuntimeError('Complete unique native distant map list required')
        distant=surface.get('native',{}).get('distant_terrain',{})
        if not distant.get('passed') or distant.get('expected')!=113 or distant.get('loaded_levels')!=113:
            raise RuntimeError('Native survey must prove every distant level and its collision/visibility settings')
        maps+=distant_maps
    if len(data['tiles'])!=113:raise RuntimeError('Incomplete terrain map list')
    dotnet=ENGINE/'Engine/Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'
    uat=ENGINE/'Engine/Binaries/DotNET/AutomationTool/AutomationTool.dll'
    # RunUAT.bat goes through cmd.exe's 8191-character ceiling. The complete
    # near+far map list needs native CreateProcess, with the same bundled SDK.
    command=[str(dotnet),str(uat),'BuildCookRun','-project='+str(project/'SoffumbergoLab.uproject'),
             '-noP4','-platform=Win64','-target=SoffumbergoLab','-clientconfig=Development','-build','-cook','-stage','-pak',
             '-archive','-archivedirectory='+str(archive),'-unattended','-utf8output','-nocompileeditor','-nodebuginfo','-map='+'+'.join(maps)]
    # Cooking produces target-platform shaders offline. It must not open a
    # renderer during the current power-delivery investigation.
    command+=['-AdditionalCookerOptions=-nullrhi','-UbtArgs=-MaxParallelActions=2']
    environment=os.environ.copy()
    environment.update(DOTNET_ROOT=str(dotnet.parent),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_ROLL_FORWARD='LatestMajor',
        UE_DOTNET_VERSION='10.0',UE_DOTNET_ARCH='win-x64',UE_DOTNET_DIR=str(dotnet.parent))
    environment['PATH']=str(dotnet.parent)+os.pathsep+environment.get('PATH','')
    for key in ['VisualStudioDir','VSSKUEDITION','PkgDefApplicationConfigFile','VSAPPIDDIR','VisualStudioEdition','VisualStudioVersion']:
        environment.pop(key,None)
    if len(subprocess.list2cmdline(command))>=32700:raise RuntimeError('Native Windows command line also exceeds its limit')
    launch_path=draft/('candidate_packaging_launch'+suffix+'.json')
    report_path=draft/('candidate_packaging_report'+suffix+'.json')
    log_path=draft/('candidate_uat'+suffix+'.log')
    if any(p.exists() for p in [launch_path,report_path,log_path]):raise RuntimeError('Preserve earlier export evidence')
    started=time.time();manifest={'build_id':build,'project':str(project),'archive':str(archive),
        'runtime_revision':args.revision,'attempt':args.attempt,'editor_binary_sha256':launch['native_binary_sha256'],
        'launcher':'bundled_dotnet_direct','native_command_line_characters':len(subprocess.list2cmdline(command)),
        'cook_rendering_disabled':True,'map_count':len(maps),'uat_log':str(log_path),
        'command':command,'started_unix':started,'world_sha256':sha(world),'itinerary_sha256':sha(itinerary),
        'lap_report':str(args.lap_report.resolve()),'surface_report':str(args.surface_report.resolve()),
        'protected_files_before':before,'published':False}
    launch_path.write_text(json.dumps(manifest,indent=2))
    with log_path.open('x',encoding='utf-8') as stream:
        result=subprocess.run(command,cwd=uat.parent,env=environment,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    exe=archive/'Windows/SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe'
    checks={'uat_success':result.returncode==0,'fresh_game_binary':exe.exists() and exe.stat().st_mtime>=started,
            'live_files_unchanged':all(sha(path)==value for path,value in before.items())}
    report={**manifest,'checks':checks,'packaged':all(checks.values()),'exit_code':result.returncode,
            'ended_unix':time.time(),'runtime_verified':False}
    if exe.exists():report['game_binary_sha256']=sha(exe)
    report_path.write_text(json.dumps(report,indent=2))
    if report['packaged'] and args.attempt!='v1':
        # Preserve prior evidence before updating the conventional latest-export
        # copies used by downstream verifiers. Raw attempt files never change.
        canonical_report=draft/'candidate_packaging_report.json'
        old=json.loads(canonical_report.read_text()) if canonical_report.exists() else {}
        old_attempt=old.get('attempt','v1')
        history=draft/'packaging_history'/old_attempt;history.mkdir(parents=True,exist_ok=True)
        for path,name in [(launch_path,'candidate_packaging_launch.json'),(report_path,'candidate_packaging_report.json'),(log_path,'candidate_uat.log')]:
            canonical=draft/name
            if canonical.exists():
                saved=history/name
                if saved.exists():
                    if sha(saved)!=sha(canonical):raise RuntimeError('Conflicting prior export evidence')
                else:shutil.copyfile(canonical,saved)
            shutil.copyfile(path,canonical)
    print(json.dumps(report,indent=2))
    if not report['packaged']:raise SystemExit(1)


if __name__=='__main__':main()
