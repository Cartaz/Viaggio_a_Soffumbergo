"""Exercise configured keyboard bindings through the native viewport at real 4K."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

p=argparse.ArgumentParser();p.add_argument('--packaged',action='store_true');p.add_argument('--bootstrap',action='store_true');p.add_argument('--run-id',required=True)
p.add_argument('--package-root',type=Path);p.add_argument('--world',type=Path);p.add_argument('--import-report',type=Path)
p.add_argument('--default-map',action='store_true',help='Verify startup without an explicit map override')
args=p.parse_args();root=Path(__file__).resolve().parents[1]
if args.bootstrap and not args.packaged:p.error('--bootstrap requires --packaged')
if args.package_root and (not args.packaged or args.world is None or args.import_report is None):p.error('A candidate package requires packaged mode, explicit world and import report')
if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in args.run_id):p.error('Invalid run id')
out=root/'results/input_checks'/args.run_id
if out.exists():raise RuntimeError('Preserving earlier check; choose a fresh run id')
out.mkdir(parents=True)
world=args.world.resolve() if args.world else root/'Unreal/Content/Data/circuit_driving_world.json';data=json.loads(world.read_text())
if args.package_root:
    imported=json.loads(args.import_report.read_text());assert imported['all_imported'] and imported['build_id']==data['build_id']
else:assert data['build_id']==json.loads((root/'parameters/current_road_design.json').read_text())['build_id']
package=args.package_root.resolve() if args.package_root else root/'build/DrivingWindows/Windows'
game=package/'SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe'
exe=(package/'SoffumbergoLab.exe' if args.bootstrap else game) if args.packaged else Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')
cmd=[str(exe)]
if not args.packaged:cmd.append(str(root/'Unreal/SoffumbergoLab.uproject'))
if not args.default_map:cmd+=['/Game/Maps/CircuitoGuidabile']
cmd+=['-game','-unattended','-nosplash','-nosound','-LabInputCheck',
      '-RenderOffscreen','-windowed','-ForceRes','-ResX=3840','-ResY=2160','-LabPreset=C',
      '-ExecCmds=t.MaxFPS 60,r.SkyLight.RealTimeReflectionCapture 0','-ini:GameUserSettings:[/Script/Engine.GameUserSettings]:FrameRateLimit=60',
      '-ini:Engine:[SystemSettings]:t.MaxFPS=60,[SystemSettings]:r.SkyLight.RealTimeReflectionCapture=0',
      '-LabRunId='+args.run_id,'-LabOutput='+str(out),'-abslog='+str(out/'engine.log')]
binary=game if args.packaged else root/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoLab.dll'
manifest={'command':cmd,'build_id':data['build_id'],'packaged':args.packaged,
          'bootstrap':args.bootstrap,'bootstrap_sha256':hashlib.sha256(exe.read_bytes()).hexdigest() if args.bootstrap else None,
          'runtime_world_sha256':hashlib.sha256(world.read_bytes()).hexdigest(),
          'runtime_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
(out/'launch_manifest.json').write_text(json.dumps(manifest,indent=2));(out/'input_world.json').write_bytes(world.read_bytes())
started=time.time()
with (out/'console.log').open('w') as stream:
    process=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
native=out/(args.run_id+'_input.json');meta=out/(args.run_id+'.json')
for path in [native,meta]:
    if not path.exists() or path.stat().st_mtime<started:raise RuntimeError('No fresh result: '+str(path))
result=json.loads(native.read_text());vehicle=json.loads(meta.read_text())
checks={'configured_keys':result['passed'],'engine_exit':process.returncode==0,
        'actual_world_generation':vehicle.get('road_world_build_id')==data['build_id'],
        'actual_world_payload':vehicle.get('road_world_data_sha1')==hashlib.sha1(world.read_bytes()).hexdigest(),
        'full_vehicle':vehicle['final_assets_loaded'],'actual_mass':vehicle['mass_measurement_valid'] and abs(vehicle['mass_kg']-1605)<.1,
        'one_requested_reset':vehicle['user_resets']==1,'startup_wait_only':vehicle['terrain_wait_episodes']<=1,
        'actual_4k_viewport':vehicle.get('viewport_width')==3840 and vehicle.get('viewport_height')==2160,
        'actual_frame_rate_cap':abs(vehicle.get('graphics_settings',{}).get('t.MaxFPS',-1)-60)<.01,
        'sky_capture_disabled_from_engine_startup':'Set CVar [[r.SkyLight.RealTimeReflectionCapture:0]]' in (out/'engine.log').read_text(encoding='utf-8',errors='replace')}
report={**manifest,'passed':all(checks.values()),'checks':checks,'native':result,
        'camera_visibility_reviewed':False,'full_lap_verified':False}
(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if not report['passed']:raise SystemExit(1)
