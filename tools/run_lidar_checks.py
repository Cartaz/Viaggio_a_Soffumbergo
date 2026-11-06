"""Execute real Chaos vehicle checks on the saved LiDAR map, not on a plane."""
import csv
import json
import math
from pathlib import Path
import subprocess
import argparse
import hashlib
import time

parser=argparse.ArgumentParser()
parser.add_argument('--packaged',action='store_true')
parser.add_argument('--render',action='store_true')
parser.add_argument('--preset',choices=['A','B','C'],default='C')
parser.add_argument('--capture',action='store_true')
parser.add_argument('--circuit',action='store_true',help='Verify the streamed full-territory map at the diagnostic spawn')
parser.add_argument('--driving',action='store_true',help='Verify the built carriageway with the actual Yaris')
parser.add_argument('--run-id',help='Preserve a separate named set of checks')
args=parser.parse_args()
if args.driving:args.circuit=True
map_path='/Game/Maps/CircuitoGuidabile' if args.driving else '/Game/Maps/CircuitoSoffumbergo' if args.circuit else '/Game/Maps/ValleLiDAR'

ROOT=Path(__file__).resolve().parents[1]
ENGINE=Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')
if args.packaged:ENGINE=ROOT/('build/DrivingWindows/Windows' if args.driving else 'build/CircuitWindows/Windows' if args.circuit else 'build/Windows')/'SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe'
label='lidar_vehicle_packaged' if args.packaged else 'lidar_vehicle'
if args.circuit:label=label.replace('lidar_vehicle','circuit_vehicle')
if args.driving:label=label.replace('circuit_vehicle','road_vehicle')
if args.render:label+='_rendered_'+args.preset
OUTPUT=ROOT/'results'/label
if args.run_id:
    if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in args.run_id):raise ValueError('Invalid run id')
    OUTPUT=OUTPUT/args.run_id
    if OUTPUT.exists():raise RuntimeError('Preserving earlier checks; choose a fresh run id')
OUTPUT.mkdir(parents=True,exist_ok=True)
spawn=json.loads((ROOT/'parameters/terrain_spawn.json').read_text())
world_data=None
if args.driving:
    world_bytes=(ROOT/'Unreal/Content/Data/circuit_driving_world.json').read_bytes();world_data=json.loads(world_bytes)
    assert world_data['build_id']==json.loads((ROOT/'parameters/current_road_design.json').read_text())['build_id']
    spawn=world_data['spawn'];(OUTPUT/'input_world.json').write_bytes(world_bytes)
launch={'map':map_path,'rendering':args.render,'packaged':args.packaged,'run_id':args.run_id,
        'build_id':world_data['build_id'] if world_data else None,
        'runtime_binary_sha256':hashlib.sha256((ENGINE if args.packaged else ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoLab.dll').read_bytes()).hexdigest(),
        'runtime_world_sha256':hashlib.sha256(world_bytes).hexdigest() if world_data else None}
(OUTPUT/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
yaw=math.radians(spawn['yaw_deg'])
reports=[]
for test in ['LIDAR_STATIC','LIDAR_DRIVE','LIDAR_REVERSE']:
    run=('road_' if args.driving else 'circuit_' if args.circuit else '')+test.lower()+('_rendered' if args.render else '_120')
    command=[str(ENGINE)]
    if not args.packaged:command.append(str(ROOT/'Unreal/SoffumbergoLab.uproject'))
    command+=[map_path,'-game','-unattended','-nosplash',
              '-LabTest='+test,'-LabRunId='+run,'-LabOutput='+str(OUTPUT),'-abslog='+str(OUTPUT/(run+'.log'))]
    if args.render:
        command+=['-RenderOffscreen','-windowed','-ResX=3840','-ResY=2160','-ForceRes','-NoVSync','-LabPreset='+args.preset]
        if args.capture and test=='LIDAR_STATIC':command+=['-LabCapture','-LabCaptureAt=8']
    else:command+=['-nullrhi','-UseFixedTimeStep','-FPS=120']
    started=time.time()
    with (OUTPUT/(run+'_console.log')).open('w') as stream:
        result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError(f'{test}: engine exit {result.returncode}')
    for name in [run+'.json',run+'.csv']:
        path=OUTPUT/name
        if not path.exists() or path.stat().st_mtime<started:raise RuntimeError('Missing fresh output '+name)
    metadata=json.loads((OUTPUT/(run+'.json')).read_text())
    rows=list(csv.DictReader((OUTPUT/(run+'.csv')).open()))
    tail=rows[-40:]
    speed=lambda r:math.sqrt(sum(float(r[k])**2 for k in ['vx_m_s','vy_m_s','vz_m_s']))
    max_speed=max(map(speed,rows));final_speed=max(map(speed,tail))
    start,end=rows[40],rows[-1]
    dx=float(end['x_m'])-float(start['x_m']);dy=-(float(end['y_m'])-float(start['y_m']))
    forward=dx*math.cos(yaw)+dy*math.sin(yaw)
    contacts=min(sum(int(r[k+'_contact']) for k in ['FL','FR','RL','RR']) for r in tail)
    inverted=any(int(r['inverted']) for r in rows)
    checks={'engine_executed':metadata['status']=='executed',
            'correct_map':metadata['geographic_scene'],'all_final_assets':metadata['final_assets_loaded'],
            'full_dynamic_mass':metadata.get('mass_measurement_valid',False) and abs(metadata.get('mass_kg',0)-1605)<0.1,
            'no_recovery':metadata.get('user_resets',0)==0,
            'not_inverted':not inverted,'four_wheel_support_at_end':contacts==4,
            'braked_at_end':final_speed<0.12,'full_duration':metadata['simulated_s']>=14.9}
    if args.render:checks['actual_4k_viewport']=metadata.get('viewport_width')==3840 and metadata.get('viewport_height')==2160
    if args.circuit:
        checks['startup_wait_only']=metadata['terrain_wait_episodes']<=1
        checks['streaming_world_executed']='CIRCUIT_WORLD tiles=113' in (OUTPUT/(run+'.log')).read_text(errors='replace')
    if test=='LIDAR_STATIC':checks['held_position']=math.hypot(dx,dy)<0.25
    elif test=='LIDAR_DRIVE':checks['forward_motion']=forward>0.5 and max_speed>0.3
    else:checks['reverse_motion']=forward< -0.5 and max_speed>0.3
    report={'test':test,'passed':all(checks.values()),'checks':checks,'max_speed_m_s':max_speed,
            'final_max_speed_m_s':final_speed,'forward_displacement_m':forward,'end_contacts':contacts,
            'frames':len(rows),'rendering':args.render,'packaged':args.packaged,'visual_quality_verified':False}
    report['map']=map_path
    report['terrain_wait_episodes']=metadata.get('terrain_wait_episodes',0)
    report['scope']='15-second spawn maneuvers; not a driven complete itinerary'
    reports.append(report);print(json.dumps(report),flush=True)
summary={**launch,'passed':all(r['passed'] for r in reports),'runs':reports}
(OUTPUT/'checks.json' if args.run_id else ROOT/'results'/(label+'_checks.json')).write_text(json.dumps(summary,indent=2))
if not all(r['passed'] for r in reports):raise SystemExit(1)
