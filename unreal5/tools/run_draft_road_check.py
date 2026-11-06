"""Execute a versioned road draft without activating or replacing the live game.

Unmodified native Editor code runs in a QA project with copied configuration,
identical native DLLs, draft input data and junctions to the imported assets.
Exact runtime signatures must prove the draft, rather than active loose data,
was loaded. The live project and packaged game never change.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
import _winapi
import sys

ROOT=Path(__file__).resolve().parents[1]
ENGINE=Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64')


def sha(path,algorithm='sha256'):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,algorithm).hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--draft',type=Path,required=True);p.add_argument('--run-id',required=True)
    p.add_argument('--mode',choices=['survey','lap'],default='survey')
    p.add_argument('--distance',type=float,default=0)
    p.add_argument('--approach-index',type=int,help='Partial local probe: start 20 route segments before this diagnostic endpoint')
    p.add_argument('--timeout',type=int,default=1800)
    p.add_argument('--background-log',type=Path,help='Persist verifier output when launched as an independent hidden worker')
    args=p.parse_args()
    if args.background_log:
        sys.stdout=args.background_log.open('w',buffering=1);sys.stderr=sys.stdout
    if not re.fullmatch('[a-z0-9_]+',args.run_id):p.error('Use a simple unique run id')
    draft=args.draft.resolve()
    imported=json.loads((draft/'import_report.json').read_text())
    world=draft/'circuit_driving_world.json';data=json.loads(world.read_text())
    itinerary=draft/'circuit_itinerary.json'
    assert imported['all_imported'] and imported['build_id']==data['build_id']
    assert json.loads(itinerary.read_text())['build_id']==data['build_id']
    if args.approach_index is not None and (args.mode!='lap' or args.distance<=0):p.error('A local approach requires lap mode and a positive distance bound')
    active_paths=[ROOT/'parameters/current_road_design.json',ROOT/'results/current_road_import.json',
                  ROOT/'Unreal/Content/Data/circuit_driving_world.json',ROOT/'Unreal/Content/Data/circuit_itinerary.json',
                  ROOT/'Unreal/Content/Maps/CircuitoGuidabile.umap',
                  ROOT/'build/DrivingWindows/Windows/SoffumbergoLab/Content/Paks/SoffumbergoLab-Windows.pak']
    before={str(path):sha(path) for path in active_paths}
    out=ROOT/'results/road_draft_checks'/args.run_id
    if out.exists():raise RuntimeError('Preserve previous check; choose a fresh run id')
    out.mkdir(parents=True)
    qa=out/'UnrealProject';qa.mkdir()
    original=ROOT/'Unreal'
    shutil.copyfile(original/'SoffumbergoLab.uproject',qa/'SoffumbergoLab.uproject')
    shutil.copytree(original/'Config',qa/'Config')
    (qa/'Binaries/Win64').mkdir(parents=True)
    for binary in (original/'Binaries/Win64').iterdir():
        if binary.suffix.lower() in ['.dll','.modules','.target']:
            shutil.copyfile(binary,qa/'Binaries/Win64'/binary.name)
    (qa/'Content').mkdir()
    for item in (original/'Content').iterdir():
        if item.name=='Data':shutil.copytree(item,qa/'Content/Data')
        elif item.is_dir():
            # Native, task-owned directory links. No source assets are copied,
            # moved, deleted or edited by this read-only runtime check.
            _winapi.CreateJunction(str(item),str(qa/'Content'/item.name))
        elif item.is_file():shutil.copyfile(item,qa/'Content'/item.name)
    for path in [world,itinerary]:
        saved=out/path.name;shutil.copyfile(path,saved)
        shutil.copyfile(saved,qa/'Content/Data'/path.name)
    if args.approach_index is not None:
        local=json.loads((out/'circuit_itinerary.json').read_text());index=args.approach_index
        if not 20<index<local['stops'][1]['index']:raise ValueError('Local probe must end before the second real stop')
        import math
        points=local['points_cm'];a=points[index-1];b=points[index]
        local['stops'][0].update({'index':index,'position_cm':b,'arrival_yaw_rad':math.atan2(b[1]-a[1],b[0]-a[0]),'name':'Diagnostic_bank_endpoint'})
        local['maneuvers'][0]['index']=index;local['maneuvers'][0]['name']='Diagnostic_bank_endpoint'
        import numpy as np
        length=float(np.linalg.norm(np.diff(np.asarray(points[index-20:index+1])[:,:2],axis=0),axis=1).sum()/100)
        if args.distance>=length-1:raise ValueError('Local probe must finish before the diagnostic endpoint and its unused maneuver')
        (out/'circuit_itinerary.json').write_text(json.dumps(local))
        shutil.copyfile(out/'circuit_itinerary.json',qa/'Content/Data/circuit_itinerary.json')
    command=[str(ENGINE/'UnrealEditor-Cmd.exe'),str(qa/'SoffumbergoLab.uproject'),
             '/Game/Maps/CircuitoGuidabile','-game','-unattended','-nosplash','-nosound',
             '-nullrhi',
             '-LabRunId='+args.run_id,'-LabOutput='+str(out),'-abslog='+str(out/'engine.log')]
    if args.mode=='survey':command+=['-CircuitRoadSurvey']
    else:
        command+=['-CircuitAutoDrive','-LabUncapped','-UseFixedTimeStep','-FPS=120']
        if args.distance:command+=['-CircuitDistanceLimit='+str(args.distance)]
        if args.approach_index is not None:command+=['-CircuitTestStop=0','-CircuitTestApproach']
    started=time.time()
    launch={'command':command,'build_id':data['build_id'],'mode':args.mode,'rendering':False,
            'world_sha1':sha(world,'sha1'),'itinerary_sha1':sha(out/'circuit_itinerary.json','sha1'),
            'local_approach_index':args.approach_index,'distance_limit_m':args.distance,
            'native_binary_sha256':sha(ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoLab.dll'),
            'qa_project':str(qa),'qa_native_binary_sha256':sha(qa/'Binaries/Win64/UnrealEditor-SoffumbergoLab.dll'),
            'active_files_before':before,'started_unix':started}
    if launch['qa_native_binary_sha256']!=launch['native_binary_sha256']:raise RuntimeError('QA physics code differs')
    (out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
    with (out/'console.log').open('w') as stream:
        result=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        launch['native_pid']=result.pid
        (out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
        # This is an observation interval, never permission to kill or restart
        # a live native check. Keep waiting on the same process after expiry.
        while True:
            try:
                result.wait(timeout=max(1,args.timeout));break
            except subprocess.TimeoutExpired:
                with (out/'observation_timeouts.jsonl').open('a') as observations:
                    observations.write(json.dumps({'unix':time.time(),'native_pid':result.pid,'still_live':result.poll() is None})+'\n')
    checks={'native_exit':result.returncode==0,'active_files_unchanged':all(sha(path)==value for path,value in before.items())}
    if args.mode=='survey':
        path=out/'circuit_road_survey.json'
        native=json.loads(path.read_text(encoding='utf-8-sig'))
        checks.update({'fresh_report':path.stat().st_mtime>=started,'native_surface_checks':native['passed'],
                       'actual_world_generation':native.get('build_id')==data['build_id'],
                       'actual_world_payload':native.get('world_data_sha1')==launch['world_sha1'],
                       'expected_probes':native['expected']==len(data['road_survey_points_cm'])+len(data['road_void_probes_cm']),
                       'underdeck_voids':native['void_checks']==native['void_clear']==len(data['road_void_probes_cm'])})
        expected_distant=sum(bool(t.get('distant_map')) for t in data['tiles'])
        if expected_distant:
            distant=native.get('distant_terrain',{})
            checks.update({'native_distant_levels':distant.get('passed') and distant.get('expected')==distant.get('loaded_levels')==distant.get('proxy_actors')==expected_distant==113,
                'distant_physics_safe':distant.get('collision_violations')==distant.get('shadow_violations')==0,
                'distant_visibility_matches_near':distant.get('visibility_mismatches')==0 and distant.get('visible_proxies',0)>0 and distant.get('hidden_proxies',0)>0,
                'distant_actual_visibility_transitions':distant.get('hide_changes',0)>0 and distant.get('show_changes',0)>0})
    else:
        path=out/(args.run_id+'_drive.json');native=json.loads(path.read_text(encoding='utf-8-sig'))
        vehicle=json.loads((out/(args.run_id+'.json')).read_text(encoding='utf-8-sig'))
        scope=native['finished'] and native['partial_diagnostic'] and not native['failed'] and native['driven_m']>=args.distance if args.distance else native['passed']
        checks.update({'fresh_report':path.stat().st_mtime>=started,'requested_scope_completed':scope,
                       'actual_world_generation':vehicle.get('road_world_build_id')==data['build_id'],
                       'actual_world_payload':vehicle.get('road_world_data_sha1')==launch['world_sha1'],
                       'actual_itinerary_payload':native.get('itinerary_sha1')==launch['itinerary_sha1'],
                       'real_vehicle':vehicle['final_assets_loaded'] and vehicle['mass_measurement_valid'] and abs(vehicle['mass_kg']-1605)<.1,
                       'no_recovery':vehicle['user_resets']==0,'startup_wait_only':vehicle['terrain_wait_episodes']<=1})
    report={'passed':all(checks.values()),'build_id':data['build_id'],'checks':checks,
            'mode':args.mode,'rendering':False,'packaged':False,'native':native,
            'full_lap_passed':args.mode=='lap' and not args.distance and all(checks.values()),
            'scope':'QA project with identical native code and imported asset links; active source world, persistent map and packaged build preserved',
            'ended_unix':time.time()}
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
