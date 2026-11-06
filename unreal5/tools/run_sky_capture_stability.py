"""Long 4K/60 hold at an exact prior crash spawn, with physics and sky visible.

Only the isolated QA profile and startup sky-capture switch differ. This is a
single-location stability diagnostic, never a full-route or root-cause claim.
"""
import argparse,hashlib,json,shutil,subprocess,time,_winapi
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--draft',type=Path,required=True)
 p.add_argument('--crash-case',type=Path,required=True);p.add_argument('--run-id',required=True)
 p.add_argument('--seconds',type=int,default=600);args=p.parse_args()
 if not args.run_id.replace('_','').isalnum() or not 60<=args.seconds<=1800:p.error('Safe unique id and 60-1800 seconds required')
 draft=args.draft.resolve();crash=args.crash_case.resolve()
 imported=json.loads((draft/'import_report.json').read_text());assert imported['all_imported']
 source=json.loads((crash/'launch_manifest.json').read_text());assert source['build_id']==imported['build_id']
 world=draft/'circuit_driving_world.json';route=crash/'circuit_itinerary.json'
 assert hashlib.sha1(world.read_bytes()).hexdigest()==source['runtime_world_sha1']
 assert sha(route)==source['qa_itinerary_sha256']
 out=ROOT/'results/sky_stability'/args.run_id;qa=ROOT/'build/SkyStabilityQA'/args.run_id/'UnrealProject'
 if out.exists() or qa.exists():raise RuntimeError('Preserve earlier trial')
 out.mkdir(parents=True);qa.mkdir(parents=True)
 original=ROOT/'Unreal';shutil.copyfile(original/'SoffumbergoLab.uproject',qa/'SoffumbergoLab.uproject')
 shutil.copytree(original/'Config',qa/'Config');shutil.copytree(original/'Binaries',qa/'Binaries',ignore=shutil.ignore_patterns('*.pdb'))
 (qa/'Content').mkdir()
 for item in (original/'Content').iterdir():
  if item.name=='Data':shutil.copytree(item,qa/'Content/Data')
  elif item.is_dir():_winapi.CreateJunction(str(item),str(qa/'Content'/item.name))
  else:shutil.copyfile(item,qa/'Content'/item.name)
 shutil.copyfile(world,qa/'Content/Data/circuit_driving_world.json');shutil.copyfile(route,qa/'Content/Data/circuit_itinerary.json')
 profiles=qa/'Content/Data/profiles.json';data=json.loads(profiles.read_text())
 data['sky_stability_hold']={'duration_s':args.seconds,'keys':[[0,0,1,0],[args.seconds,0,1,0]]}
 profiles.write_text(json.dumps(data))
 dll=original/'Binaries/Win64/UnrealEditor-SoffumbergoLab.dll';assert sha(dll)==source['native_binary_sha256']
 protected=[dll,original/'Content/Data/circuit_driving_world.json',original/'Content/Data/circuit_itinerary.json',ROOT/'parameters/current_road_design.json',world,route]
 before={str(f):sha(f) for f in protected}
 exe=Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')
 command=[str(exe),str(qa/'SoffumbergoLab.uproject'),'/Game/Maps/CircuitoGuidabile','-game','-unattended','-nosplash','-nosound',
  '-CircuitTestStop=0','-LabTest=sky_stability_hold','-LabRunId='+args.run_id,'-LabOutput='+str(out),'-abslog='+str(out/'engine.log'),
  '-RenderOffscreen','-windowed','-ForceRes','-ResX=3840','-ResY=2160','-LabPreset=C',
  '-ExecCmds=t.MaxFPS 60,r.SkyLight.RealTimeReflectionCapture 0',
  '-ini:GameUserSettings:[/Script/Engine.GameUserSettings]:FrameRateLimit=60',
  '-ini:Engine:[SystemSettings]:t.MaxFPS=60,[SystemSettings]:r.SkyLight.RealTimeReflectionCapture=0']
 started=time.time();launch={'command':command,'run_id':args.run_id,'build_id':source['build_id'],'started_unix':started,
  'requested_duration_s':args.seconds,'native_dll_sha256':sha(dll),'world_sha1':source['runtime_world_sha1'],
  'qa_itinerary_sha256':sha(route),'initial_spawn_reference':source['initial_position_cm'],'protected_before':before,
  'scope':'Braked full car with physics active at exact previous crash spawn, 4K/cap60/one-time sky capture. No full-route claim.'}
 with (out/'console.log').open('w') as log:
  process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  launch['native_pid']=process.pid;(out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
  print(json.dumps({'native_pid':process.pid,'started':started,'duration_s':args.seconds}),flush=True)
  try:code=process.wait(timeout=args.seconds+300)
  except subprocess.TimeoutExpired:
   (out/'observation_timeout.json').write_text(json.dumps({'native_pid':process.pid,'terminal':False,'native_still_running':process.poll() is None}))
   raise RuntimeError('Observation expired; inspect the same native PID without restarting')
 meta_path=out/(args.run_id+'.json');checks={'native_exit':code==0,'fresh_native_report':meta_path.exists() and meta_path.stat().st_mtime>=started,
  'protected_files_unchanged':all(sha(f)==h for f,h in before.items())}
 meta=json.loads(meta_path.read_text(encoding='utf-8-sig')) if checks['fresh_native_report'] else None
 if meta:
  checks.update({'duration_completed':meta['status']=='executed' and meta['simulated_s']>=args.seconds-.1,
   'actual_world':meta['road_world_build_id']==source['build_id'] and meta['road_world_data_sha1']==source['runtime_world_sha1'],
   'full_car_physics':meta['final_assets_loaded'] and meta['mass_measurement_valid'] and abs(meta['mass_kg']-1605)<.1 and not meta['physics_disabled_for_graphics'],
   'actual_4k':meta['viewport_width']==3840 and meta['viewport_height']==2160,
   'actual_cap60':meta['graphics_settings']['t.MaxFPS']==60 and meta['user_settings_frame_rate_limit']==60,
   'sky_capture_disabled':meta['sky_light_count']>0 and meta['realtime_sky_light_count']==0,
   'no_resets':meta['user_resets']==0})
 text=(out/'engine.log').read_text(encoding='utf-8',errors='replace')
 checks['sky_disabled_from_startup']='Set CVar [[r.SkyLight.RealTimeReflectionCapture:0]]' in text
 checks['no_gpu_hang']='DXGI_ERROR_DEVICE_HUNG' not in text and 'GPU Crashed or D3D Device Removed' not in text
 report={'passed':all(checks.values()),'checks':checks,'native_exit_code':code,'build_id':source['build_id'],
  'duration_requested_s':args.seconds,'native_metadata':meta,'ended_unix':time.time(),'scope':launch['scope'],'root_cause_proven':False}
 (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({'passed':report['passed'],'checks':checks}),flush=True)
 if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
