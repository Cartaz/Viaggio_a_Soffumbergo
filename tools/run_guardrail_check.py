"""Low-speed physical guardrail contact and reverse release with the full Yaris.

Only diagnostic initial spawn and ordinary controls are changed in an isolated
QA project/package. No collision, terrain, vehicle, pose or velocity correction
is used after spawn. A ray survey alone cannot establish vehicle containment.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import struct
import time
import _winapi
import numpy as np
import shapely
from road_surface import RoadSurface

ROOT=Path(__file__).resolve().parents[1]
ENGINE=Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64')


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def rotate(q,v):
    # Native CSV reflects Y: convert its quaternion back to Unreal first.
    xyz=q[:,1:]*np.array([-1,1,-1]);w=q[:,0,None]
    return v[None]+2*np.cross(xyz[:,None,:],np.cross(xyz[:,None,:],v[None])+w[:,:,None]*v[None])


def main():
    p=argparse.ArgumentParser();p.add_argument('--draft',type=Path,required=True)
    p.add_argument('--run-id',required=True);p.add_argument('--packaged',action='store_true')
    p.add_argument('--render',action='store_true')
    p.add_argument('--control',default='costalunga_rock_bank')
    p.add_argument('--reverse-gas',type=float,default=.12)
    p.add_argument('--reverse-duration',type=float,default=1.45);args=p.parse_args()
    if not .3<=args.reverse_duration<=2:p.error('Reverse duration must stay within the bounded trial')
    if not .05<=args.reverse_gas<=1:p.error('Reverse pedal must stay within ordinary input limits')
    if not args.run_id.replace('_','').isalnum():p.error('Use a fresh simple run id')
    draft=args.draft.resolve();imported=json.loads((draft/'import_report.json').read_text())
    m=json.loads(Path(imported['manifest']).read_text());build=m['build_id']
    world=draft/'circuit_driving_world.json';itinerary_path=draft/'circuit_itinerary.json'
    if not imported['all_imported'] or json.loads(world.read_text())['build_id']!=build:raise RuntimeError('Unverified input world')
    out=ROOT/'results/guardrail_checks'/args.run_id
    if out.exists():raise RuntimeError('Preserve earlier physical contact check')
    out.mkdir(parents=True)
    control=next(c for c in m['roadside_structures']['config']['controls'] if c['id']==args.control)
    record=next(r for r in m['roadside_structures']['records'] if r['observed_control']==args.control and r['kind']=='metal')
    mesh=json.loads(Path(record['source']).read_text())
    solids=(np.asarray(mesh['vertices_cm'])+np.asarray(record['location_cm'])).reshape(-1,8,3)/100
    beams=[s for s in solids if np.linalg.norm(s[1,:2]-s[0,:2])>.4]
    trial_selection={'method':'Nearest main beam to the observed control'}
    if control.get('guardrail_extent'):
        # The car faces across the rail during this containment trial. Its
        # complete lateral footprint must meet a real interior rail section,
        # rather than asking a physical terminal to contain an open approach.
        lengths=np.asarray([np.linalg.norm(s[1,:2]-s[0,:2]) for s in beams])
        stations=np.cumsum(lengths)-lengths/2;total=float(lengths.sum());clearance=2.
        interior=[s for s,station in zip(beams,stations) if clearance<=station<=total-clearance]
        if not interior:raise RuntimeError('No interior rail section for complete-body contact trial')
        beams=interior;trial_selection={'method':'Nearest main beam with 2 m of real run to both ends','run_length_m':total,'minimum_end_clearance_m':clearance}
    solid=min(beams,key=lambda s:np.linalg.norm(s[:4,:2].mean(axis=0)-control['center_UE_xy_m']))
    center=solid[:4,:2].mean(axis=0)
    tangent=solid[1,:2]-solid[0,:2];tangent/=np.linalg.norm(tangent)
    normal=np.array([-tangent[1],tangent[0]])
    axis=np.asarray(m['profile_UE_cm'])[:,:2]/100
    near=axis[np.argmin(np.linalg.norm(axis-center,axis=1))]
    if np.dot(normal,center-near)<0:normal=-normal
    position=center-normal*2.5
    surface=RoadSurface(m);z,distance=surface.sample(position*100)
    if distance[0]>.01:raise RuntimeError('Initial vehicle center is outside asphalt')
    position_cm=[*list(position*100),float(z[0])];yaw=math.atan2(normal[1],normal[0])
    itinerary=json.loads(itinerary_path.read_text());itinerary['stops'][0]['position_cm']=position_cm
    itinerary['stops'][0]['arrival_yaw_rad']=yaw;itinerary['diagnostic_initial_spawn_only']=True
    reverse_end=8.55+args.reverse_duration
    profile={'duration_s':13,'keys':[[0,0,1,0],[2.5,0,1,0],[2.55,.12,0,0],[7,.12,0,0],
        [7.05,0,1,0],[8.5,0,1,0],[8.55,-args.reverse_gas,0,0],[reverse_end,-args.reverse_gas,0,0],[reverse_end+.05,0,1,0],[13,0,1,0]]}
    profiles=json.loads((ROOT/'Unreal/Content/Data/profiles.json').read_text());profiles['GUARDRAIL_QA']=profile
    for name,data in [('profiles.json',profiles),('circuit_itinerary.json',itinerary)]:
        (out/name).write_text(json.dumps(data))
    protected=[ROOT/'parameters/current_road_design.json',ROOT/'Unreal/Content/Data/circuit_driving_world.json',
               ROOT/'Unreal/Content/Data/circuit_itinerary.json']
    before={str(path):sha(path) for path in protected}
    package_before={}
    if args.packaged:
        pack=json.loads((draft/'candidate_packaging_report.json').read_text())
        if not pack['packaged'] or pack['world_sha256']!=sha(world):raise RuntimeError('Package differs from requested candidate')
        source=Path(pack['archive'])/'Windows';qa=ROOT/'build/GuardrailQA'/args.run_id/'Windows'
        if qa.exists():raise RuntimeError('Preserve earlier QA package')
        shutil.copytree(source,qa)
        for path in [Path('SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe')]+[
            Path('SoffumbergoLab/Content/Paks/SoffumbergoLab-Windows.'+suffix) for suffix in ['pak','ucas','utoc']]:
            package_before[str(source/path)]=sha(source/path)
            if sha(qa/path)!=sha(source/path):raise RuntimeError('QA base copy differs')
        response=out/'pak_response.txt'
        response.write_text('\n'.join('"'+str(out/name)+'" "../../../SoffumbergoLab/Content/Data/'+name+'"'
            for name in ['profiles.json','circuit_itinerary.json']))
        patch=out/'GuardrailQA_P.pak'
        with (out/'create_pak.log').open('w') as log:
            subprocess.run([str(ENGINE/'UnrealPak.exe'),str(patch),'-Create='+str(response)],stdout=log,
                stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
        shutil.copyfile(patch,qa/'SoffumbergoLab/Content/Paks/GuardrailQA_P.pak')
        binary=qa/'SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe';command=[str(binary)]
    else:
        qa=out/'UnrealProject';qa.mkdir();original=ROOT/'Unreal'
        shutil.copyfile(original/'SoffumbergoLab.uproject',qa/'SoffumbergoLab.uproject')
        shutil.copytree(original/'Config',qa/'Config');(qa/'Binaries/Win64').mkdir(parents=True)
        for path in (original/'Binaries/Win64').iterdir():
            if path.suffix in ['.dll','.modules','.target']:shutil.copyfile(path,qa/'Binaries/Win64'/path.name)
        (qa/'Content').mkdir()
        for path in (original/'Content').iterdir():
            if path.name=='Data':shutil.copytree(path,qa/'Content/Data')
            elif path.is_dir():_winapi.CreateJunction(str(path),str(qa/'Content'/path.name))
            else:shutil.copyfile(path,qa/'Content'/path.name)
        for path in [world,out/'profiles.json',out/'circuit_itinerary.json']:shutil.copyfile(path,qa/'Content/Data'/path.name)
        binary=qa/'Binaries/Win64/UnrealEditor-SoffumbergoLab.dll'
        if sha(binary)!=sha(original/'Binaries/Win64'/binary.name):raise RuntimeError('Native QA DLL changed')
        command=[str(ENGINE/'UnrealEditor-Cmd.exe'),str(qa/'SoffumbergoLab.uproject')]
    command+=['/Game/Maps/CircuitoGuidabile','-game','-unattended','-nosplash','-nosound',
        '-LabUncapped','-LabTest=GUARDRAIL_QA','-CircuitTestStop=0',
        '-LabRunId='+args.run_id,'-LabOutput='+str(out),'-abslog='+str(out/'engine.log'),'-pak.AllowMissingUToc']
    if args.render:
        command+=['-RenderOffscreen','-windowed','-ForceRes','-ResX=3840','-ResY=2160','-LabPreset=C',
                  '-ExecCmds=t.MaxFPS 60','-LabCapture','-LabCaptureAt=6']
    else:command+=['-nullrhi','-UseFixedTimeStep','-FPS=120']
    launch={'build_id':build,'command':command,'binary_sha256':sha(binary),'world_sha1':hashlib.sha1(world.read_bytes()).hexdigest(),
        'initial_position_cm':position_cm,'barrier_center_UE_xy_m':center.tolist(),'outward_UE_xy':normal.tolist(),
        'barrier_mesh':record['id'],'started_unix':time.time(),'packaged':args.packaged,'rendering':args.render,
        'barrier_trial_selection':trial_selection,
        'chassis_dimensions_m':[3.8,1.68,.75],'chassis_center_local_m':[0,0,.7],
        'protected_before':before,'source_package_before':package_before,'scope':'One selected low-speed guardrail contact and reverse release; no crash-safety or whole-route claim'}
    (out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
    with (out/'console.log').open('w') as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        launch['native_pid']=process.pid
        (out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
        while True:
            try:
                native_code=process.wait(timeout=300)
                break
            except subprocess.TimeoutExpired:
                launch.setdefault('observation_timeouts_unix',[]).append(time.time())
                (out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
    meta=json.loads((out/(args.run_id+'.json')).read_text(encoding='utf-8-sig'))
    with (out/(args.run_id+'.csv')).open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    xyz=np.array([[float(r['x_m']),-float(r['y_m']),float(r['z_m'])] for r in rows])
    q=np.array([[float(r[k]) for k in ['qw','qx','qy','qz']] for r in rows])
    corners=np.array([[x,y,z] for x in [-1.9,1.9] for y in [-.84,.84] for z in [.325,1.075]])
    body=rotate(q,corners)+xyz[:,None,:]
    inner_plane=min(solid[:4,:2]@normal)
    front=body[:,:,:2]@normal
    gap=inner_plane-front.max(axis=1)
    elapsed=np.array([float(r['time_s']) for r in rows]);gas=np.array([float(r['throttle']) for r in rows])
    brake=np.array([float(r['brake']) for r in rows]);speed=np.linalg.norm([[float(r[k]) for k in ['vx_m_s','vy_m_s','vz_m_s']] for r in rows],axis=1)
    excursion=(xyz[:,:2]-position)@normal
    pushing=(elapsed>=3)&(elapsed<=7)&(gas>.1)&(brake<.01)
    resting_against=pushing&(gap<.12)&(gap>-.08)&(speed<.12)
    release=(elapsed>=10)&(elapsed<=13)
    contacts=np.array([[int(r[k+'_contact']) for k in ['FL','FR','RL','RR']] for r in rows]).sum(1)
    wheel_centers=np.array([[x,y,0] for x in [-1.28,1.28] for y in [-.74,.74]])
    wheel_xy=(rotate(q,wheel_centers)+xyz[:,None,:])[:,:,:2]
    _,wheel_dist=surface.sample(wheel_xy[pushing].reshape(-1,2)*100)
    keys=np.asarray(profile['keys']);input_error=max(float(np.abs(np.array([float(r[name]) for r in rows])-np.interp(elapsed,keys[:,0],keys[:,j])).max())
        for j,name in enumerate(['throttle','brake','steering_input'],1))
    checks={'native_completed':native_code==0 and meta['status']=='executed' and meta['simulated_s']>=13,
        'requested_rendering_mode':bool(meta.get('RHI')) and (meta['RHI']!='Null')==args.render,
        'actual_world_generation':meta['road_world_build_id']==build,'actual_world_payload':meta['road_world_data_sha1']==launch['world_sha1'],
        'actual_initial_spawn':np.linalg.norm(xyz[0,:2]-position)<.05,
        'full_vehicle':meta['final_assets_loaded'] and meta['mass_measurement_valid'] and abs(meta['mass_kg']-1605)<.1 and not meta['physics_disabled_for_graphics'],
        'no_reset':meta['user_resets']==0,'startup_wait_only':meta['terrain_wait_episodes']<=1,
        'actual_controls':input_error<.002,'forward_contact_approach':float(excursion[pushing].max())>.2,
        'contained_by_barrier_plane':float(gap[pushing].min())>-.08,
        'held_against_barrier_while_driving':int(resting_against.sum())>=20,
        'wheels_stay_on_asphalt_during_push':float(wheel_dist.max())<.01,
        'reverse_releases_vehicle':float(excursion[release].min())<float(excursion[pushing].max())-.2,
        'final_stationary':float(speed[elapsed>11].max())<.12,
        'contacts_after_settle':bool(np.all(contacts[elapsed>2]>=3)),
        'upright':max(abs(float(r['roll_rad'])) for r in rows)<math.radians(25),
        'requested_viewport':not args.render or meta.get('viewport_width')==3840 and meta.get('viewport_height')==2160,
        'requested_frame_cap':not args.render or abs(meta.get('graphics_settings',{}).get('t.MaxFPS',-1)-60)<.01,
        'protected_files_unchanged':all(sha(path)==value for path,value in {**before,**package_before}.items())}
    checks={k:bool(v) for k,v in checks.items()}
    report={'passed':all(checks.values()),'checks':checks,'build_id':build,'packaged':args.packaged,'rendering':args.render,
        'RHI':meta.get('RHI'),
        'sleeping_reverse_input_samples':meta.get('sleeping_reverse_input_samples'),
        'max_excursion_m':float(excursion.max()),'minimum_front_gap_m':float(gap[pushing].min()),
        'pushing_rest_samples':int(resting_against.sum()),'min_contacts_after_settle':int(contacts[elapsed>2].min()),
        'input_error':input_error,'scope':launch['scope'],'ended_unix':time.time()}
    if args.render:
        paths=[out/(args.run_id+'.png'),qa/'private/screenshots'/(args.run_id+'.png')]
        if not args.packaged:paths.append(out/'private/screenshots'/(args.run_id+'.png'))
        shot=next((path for path in paths if path.exists() and path.stat().st_mtime>=launch['started_unix']),None)
        if shot is None:shot=next((path for path in qa.rglob(args.run_id+'.png') if path.stat().st_mtime>=launch['started_unix']),None)
        report['contact_screenshot']=str(shot) if shot else None
        size=None
        if shot is not None:
            with shot.open('rb') as f:header=f.read(24)
            if header[:8]==b'\x89PNG\r\n\x1a\n':size=list(struct.unpack('>II',header[16:24]))
        checks['fresh_contact_screenshot']=shot is not None
        checks['contact_screenshot_4k']=size==[3840,2160]
        report['contact_image_size']=size;report['passed']=all(checks.values())
        report['visual_contact_reviewed']=False
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
