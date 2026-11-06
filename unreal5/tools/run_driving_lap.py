"""Drive the real Yaris by controls, retaining a fresh per-run evidence directory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import time

p=argparse.ArgumentParser()
p.add_argument('--packaged',action='store_true');p.add_argument('--render',action='store_true')
p.add_argument('--package-root',type=Path,help='Separate exported candidate; requires --packaged and explicit matching input data')
p.add_argument('--world',type=Path);p.add_argument('--itinerary',type=Path)
p.add_argument('--distance',type=float,default=0,help='Optional bounded development diagnostic, never a full lap')
p.add_argument('--run-id',default='full_lap');p.add_argument('--timeout',type=int,default=1800)
p.add_argument('--max-fps',type=float,help='Explicit rendered gameplay cap, verified from native metadata')
p.add_argument('--test-stop',type=int,choices=[0,1,2],help='Isolated initial spawn at a stop; never accepted as a full lap')
p.add_argument('--approach-stop',action='store_true',help='Include the final 20 route segments before the isolated maneuver')
p.add_argument('--depart-stop',action='store_true',help='Continue after the isolated turn up to the explicit distance bound')
args=p.parse_args();root=Path(__file__).resolve().parents[1]
if args.render and args.max_fps is None:args.max_fps=60
if args.max_fps is not None and args.max_fps>60:p.error('Rendered runs must respect the user 60 FPS ceiling')
if args.max_fps is not None and (not args.render or args.max_fps<=0):p.error('--max-fps requires rendering and a positive cap')
if args.package_root and (not args.packaged or args.world is None or args.itinerary is None):p.error('A separate package requires --packaged, --world and --itinerary')
if args.approach_stop and args.test_stop is None:p.error('--approach-stop requires --test-stop')
if args.depart_stop and (args.test_stop is None or args.distance<=0):p.error('--depart-stop requires --test-stop and a positive --distance')
out=root/'results/driving_laps'/args.run_id
if out.exists():raise RuntimeError('Preserving existing run; choose a new run id')
out.mkdir(parents=True)
data=args.itinerary.resolve() if args.itinerary else root/'Unreal/Content/Data/circuit_itinerary.json';itinerary=json.loads(data.read_text())
world=args.world.resolve() if args.world else root/'Unreal/Content/Data/circuit_driving_world.json'
assert itinerary['build_id']==json.loads(world.read_text())['build_id']
package=args.package_root.resolve() if args.package_root else root/'build/DrivingWindows/Windows'
exe=package/'SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe' if args.packaged else Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')
cmd=[str(exe)]
if not args.packaged:cmd.append(str(root/'Unreal/SoffumbergoLab.uproject'))
cmd+=['/Game/Maps/CircuitoGuidabile','-game','-unattended','-nosplash','-nosound','-CircuitAutoDrive','-LabUncapped',
      '-LabRunId='+args.run_id,'-LabOutput='+str(out),'-abslog='+str(out/'engine.log')]
if args.distance:cmd+=['-CircuitDistanceLimit='+str(args.distance)]
if args.test_stop is not None:cmd+=['-CircuitTestStop='+str(args.test_stop)]
if args.approach_stop:cmd+=['-CircuitTestApproach']
if args.depart_stop:cmd+=['-CircuitTestDeparture']
if args.render:cmd+=['-RenderOffscreen','-windowed','-ForceRes','-ResX=3840','-ResY=2160','-LabPreset=C','-LabCapture','-LabCaptureAt=8']
else:cmd+=['-nullrhi','-UseFixedTimeStep','-FPS=120']
if args.max_fps is not None:cmd+=['-ExecCmds=t.MaxFPS '+str(args.max_fps)]
started=time.time()
input_hash=hashlib.sha256(data.read_bytes()).hexdigest();world_hash=hashlib.sha256(world.read_bytes()).hexdigest()
itinerary_sha1=hashlib.sha1(data.read_bytes()).hexdigest();world_sha1=hashlib.sha1(world.read_bytes()).hexdigest()
binary=exe if args.packaged else root/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoLab.dll'
launch={'command':cmd,'started_unix':started,'build_id':itinerary['build_id'],'itinerary_sha256':input_hash,
        'runtime_world_sha256':world_hash,'runtime_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
launch['requested_max_fps']=args.max_fps
(out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
shutil.copyfile(data,out/'input_itinerary.json')
shutil.copyfile(world,out/'input_world.json')
with (out/'console.log').open('w') as log:
    process=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    launch['native_pid']=process.pid
    (out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
    while True:
        try:process.wait(timeout=max(1,args.timeout));break
        except subprocess.TimeoutExpired:
            with (out/'observation_timeouts.jsonl').open('a') as observations:
                observations.write(json.dumps({'unix':time.time(),'native_pid':process.pid,'still_live':process.poll() is None})+'\n')
file=out/(args.run_id+'_drive.json')
if process.returncode or not file.exists() or file.stat().st_mtime<started:raise RuntimeError('No fresh driving result')
result=json.loads(file.read_text());meta=json.loads((out/(args.run_id+'.json')).read_text())
scope_ok=(result['finished'] and result['partial_diagnostic'] and not result['failed'] and result['maneuvers_completed']==1) if args.test_stop is not None else (result['finished'] and result['partial_diagnostic'] and not result['failed'] and result['driven_m']>=args.distance) if args.distance else result['passed']
if args.depart_stop:scope_ok=scope_ok and result['driven_m']>=args.distance
checks={'driver_scope_completed':scope_ok,'real_full_vehicle':meta['final_assets_loaded'],
        'actual_world_generation':meta.get('road_world_build_id')==itinerary['build_id'],
        'actual_world_payload':meta.get('road_world_data_sha1')==world_sha1,
        'actual_itinerary_payload':result.get('itinerary_sha1')==itinerary_sha1,
        'actual_dynamic_mass':meta['mass_measurement_valid'] and abs(meta['mass_kg']-1605)<.1,
        'no_recovery':meta['user_resets']==0,'startup_terrain_wait_only':meta['terrain_wait_episodes']<=1,
        'rendered_4k':not args.render or meta.get('viewport_width')==3840 and meta.get('viewport_height')==2160}
if args.max_fps is not None:checks['actual_requested_frame_cap']=abs(meta.get('graphics_settings',{}).get('t.MaxFPS',-1)-args.max_fps)<.01
report={'passed_for_requested_test_scope':all(checks.values()),'full_lap_passed':args.test_stop is None and not args.distance and all(checks.values()),
        'checks':checks,'drive':result,'rendering':args.render,'packaged':args.packaged,
        'distance_limit_m':args.distance,'isolated_stop':args.test_stop,'approach_stop':args.approach_stop,'depart_stop':args.depart_stop,'command':cmd,'build_id':itinerary['build_id'],
        'itinerary_sha256':input_hash,'runtime_world_sha256':world_hash,
        'requested_max_fps':args.max_fps,
        'runtime_binary_sha256':launch['runtime_binary_sha256']}
(out/'report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
if not report['passed_for_requested_test_scope']:raise SystemExit(1)
