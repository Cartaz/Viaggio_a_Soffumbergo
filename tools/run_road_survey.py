"""Actual engine collision check along the complete built candidate carriageway."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import shutil

parser=argparse.ArgumentParser();parser.add_argument('--packaged',action='store_true')
parser.add_argument('--run-id',help='Preserve a separate named survey, including failed earlier generations')
parser.add_argument('--package-root',type=Path);parser.add_argument('--world',type=Path)
parser.add_argument('--import-report',type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
if args.package_root and (not args.packaged or args.world is None or args.import_report is None):parser.error('A candidate package requires packaged mode, explicit world and import report')
data_path=args.world.resolve() if args.world else root/'Unreal/Content/Data/circuit_driving_world.json';data=json.loads(data_path.read_text())
if not args.package_root:assert data['build_id']==json.loads((root/'parameters/current_road_design.json').read_text())['build_id'],'Latest generated geometry has not been imported'
imported=json.loads((args.import_report or root/'results/current_road_import.json').read_text())
assert imported['all_imported'] and data['build_id']==imported['build_id'],'Import evidence does not match runtime data'
out=root/'results'/('road_surface_packaged' if args.packaged else 'road_surface_editor')
if args.run_id:
    if not args.run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in args.run_id):raise ValueError('Invalid run id')
    out=out/args.run_id
    if out.exists():raise RuntimeError('Preserving earlier survey; choose a fresh run id')
out.mkdir(parents=True,exist_ok=True)
package=args.package_root.resolve() if args.package_root else root/'build/DrivingWindows/Windows'
exe=package/'SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe' if args.packaged else Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')
command=[str(exe)]
if not args.packaged:command.append(str(root/'Unreal/SoffumbergoLab.uproject'))
command+=['/Game/Maps/CircuitoGuidabile','-game','-unattended','-nullrhi','-nosound','-nosplash','-CircuitRoadSurvey',
          '-LabOutput='+str(out),'-abslog='+str(out/'engine.log')]
started=time.time()
world_hash=hashlib.sha256(data_path.read_bytes()).hexdigest()
shutil.copyfile(data_path,out/'input_world.json')
launch={'command':command,'started_unix':started,'build_id':data['build_id'],
        'world_data_sha256':world_hash,'packaged':args.packaged,
        'runtime_binary_sha256':hashlib.sha256((exe if args.packaged else root/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoLab.dll').read_bytes()).hexdigest()}
(out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
with (out/'console.log').open('w') as stream:
    with subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW) as p:
        launch['native_pid']=p.pid
        (out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
        while True:
            try:p.wait(timeout=300);break
            except subprocess.TimeoutExpired:
                with (out/'observation_timeouts.jsonl').open('a') as observations:
                    observations.write(json.dumps({'unix':time.time(),'native_pid':p.pid,'still_live':p.poll() is None})+'\n')
        launch.update({'native_exit_code':p.returncode,'ended_unix':time.time()})
        (out/'process_result.json').write_text(json.dumps(launch,indent=2))
path=out/'circuit_road_survey.json'
if p.returncode or not path.exists() or path.stat().st_mtime<started:raise RuntimeError('Road survey not freshly executed')
report=json.loads(path.read_text())
assert report.get('build_id')==data['build_id'],'Runtime road generation does not match the requested input'
assert report.get('world_data_sha1')==hashlib.sha1(data_path.read_bytes()).hexdigest(),'Runtime world payload does not match the requested input'
assert report['expected']==len(data['road_survey_points_cm'])+len(data.get('road_void_probes_cm',[]))
if data.get('road_void_probes_cm'):assert report['void_checks']==report['void_clear']==len(data['road_void_probes_cm'])
distant_count=sum(bool(t.get('distant_map')) for t in data['tiles'])
if distant_count:
    distant=report.get('distant_terrain',{})
    assert distant.get('passed') and distant.get('expected')==distant.get('loaded_levels')==distant.get('proxy_actors')==distant_count==113
    assert distant.get('collision_violations')==distant.get('shadow_violations')==distant.get('visibility_mismatches')==0
    assert distant.get('hide_changes',0)>0 and distant.get('show_changes',0)>0
manifest={'build_id':data['build_id'],'command':command,'packaged':args.packaged,
          'world_data_sha256':world_hash,'passed':report['passed'],
          'run_id':args.run_id,'runtime_binary_sha256':hashlib.sha256((exe if args.packaged else root/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoLab.dll').read_bytes()).hexdigest()}
if distant_count:manifest['distant_terrain']=report['distant_terrain']
(out/'run_manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(report))
if not report['passed']:raise SystemExit(1)
