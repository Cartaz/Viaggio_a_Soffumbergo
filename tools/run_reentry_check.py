"""Run an off-road/reentry input curve in an isolated copy of the shipped game.

The executable, terrain, road, vehicle and physics remain byte-identical to the
production package. A diagnostic pak overrides only the input curve and initial
spawn. It never replaces data in the production directory or during its tests.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import time
import numpy as np
import shapely
from road_surface import RoadSurface

ROOT=Path(__file__).resolve().parents[1]
PAK=Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealPak.exe')


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def make_profile(candidate, reverse_scale=1):
    station=np.asarray(candidate['profile_s_m']);height=np.asarray(candidate['surface_height_m'])
    keys=[];duration=14+8*reverse_scale+5
    for t in np.arange(0,duration+.001,.05):
        if 3<=t<11:
            u=t-3;direction=1;scale=1
        elif 14<=t<14+8*reverse_scale:
            u=(t-14)/reverse_scale;direction=-1;scale=reverse_scale
        else:
            keys.append([round(float(t),6),0,1,0]);continue
        if u<1:s=.6*u*u;v=1.2*u;acceleration=1.2
        elif u<7:s=.6+1.2*(u-1);v=1.2;acceleration=0
        else:s=7.8+1.2*(u-7)-.6*(u-7)**2;v=1.2*(8-u);acceleration=-1.2
        if direction<0:s=8.4-s
        gradient=(np.interp(s+1.28,station,height)-np.interp(s-1.28,station,height))/2.56
        force=1605*acceleration*direction/(scale*scale)+1605*9.81*gradient+120*direction
        if direction*force>=0:gas=force/6500;brake=0
        else:gas=0;brake=abs(force)/16000
        keys.append([round(float(t),6),float(np.clip(gas,-1,1)),float(np.clip(brake,0,1)),0])
    return {'duration_s':float(duration),'keys':keys,
            'method':'open-loop ordinary throttle/brake/steering; symmetric low-speed excursion, no pose/velocity changes',
            'desired_excursion_m':8.4,'reverse_time_scale':reverse_scale}


def pulse_profile(out_seconds, reverse_seconds, brake):
    back=3+out_seconds+3;end=back+reverse_seconds
    return {'duration_s':end+5,
            'keys':[[0,0,1,0],[2.95,0,1,0],[3,.12,0,0],
                    [3+out_seconds-.05,.12,0,0],[3+out_seconds,0,brake,0],
                    [3+out_seconds+2,0,brake,0],[3+out_seconds+2.05,0,1,0],
                    [back-.05,0,1,0],[back,-.2,0,0],
                    [end-.05,-.2,0,0],[end,0,brake,0],
                    [end+2,0,brake,0],[end+2.05,0,1,0],[end+5,0,1,0]],
            'method':'ordinary throttle/brake pulses and straight steering; no pose, velocity or balance changes',
            'out_seconds':out_seconds,'reverse_seconds':reverse_seconds,'deceleration_brake':brake}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run-id',required=True)
    p.add_argument('--station',type=float,default=2430)
    p.add_argument('--reverse-scale',type=float,default=1)
    p.add_argument('--pulse',action='store_true')
    p.add_argument('--out-seconds',type=float,default=5)
    p.add_argument('--reverse-seconds',type=float,default=5.5)
    p.add_argument('--pulse-brake',type=float,default=.18)
    p.add_argument('--render',action='store_true')
    p.add_argument('--prepare-only',action='store_true')
    p.add_argument('--draft',type=Path,help='Use the separately exported candidate and newly sampled candidate access set')
    p.add_argument('--candidates',type=Path)
    p.add_argument('--allow-geometric-diagnostic',action='store_true',
                   help='Explicitly test a separately flagged access that failed the conservative grade screen')
    p.add_argument('--streetview-review',type=Path,
                   help='Required observed access evidence for a geometric diagnostic')
    p.add_argument('--max-fps',type=float)
    args=p.parse_args()
    if args.render and args.max_fps is None:args.max_fps=60
    if args.max_fps is not None and args.max_fps>60:p.error('Rendered runs must respect the user 60 FPS ceiling')
    if not re.fullmatch('[a-z0-9_]+',args.run_id):p.error('Use a simple unique diagnostic run id')
    if not .5<=args.reverse_scale<=2:p.error('Reverse scale must stay within the planned low-speed trial')
    if args.max_fps is not None and (not args.render or not math.isfinite(args.max_fps) or args.max_fps<=0):
        p.error('A positive finite FPS limit requires rendering')
    world=ROOT/'Unreal/Content/Data/circuit_driving_world.json'
    itinerary_path=ROOT/'Unreal/Content/Data/circuit_itinerary.json'
    if args.draft:
        draft=args.draft.resolve()
        world=draft/'circuit_driving_world.json';itinerary_path=draft/'circuit_itinerary.json'
        pack=json.loads((draft/'candidate_packaging_report.json').read_text())
        if not pack['packaged'] or digest(world)!=pack['world_sha256'] or digest(itinerary_path)!=pack['itinerary_sha256']:
            raise RuntimeError('Candidate export does not match its current data')
        imported=json.loads((draft/'import_report.json').read_text())
        manifest_path=Path(imported.get('manifest',ROOT/'terrain/road_design'/pack['build_id']/'manifest.json'))
        production=Path(pack['archive'])/'Windows'
        qa=ROOT/'build/ReentryCandidateQA'/args.run_id/'Windows'
        if not args.candidates:p.error('Candidate access must be resampled with --candidates')
    else:
        pointer=json.loads((ROOT/'parameters/current_road_design.json').read_text())
        manifest_path=Path(pointer['manifest'])
        production=ROOT/'build/DrivingWindows/Windows'
        qa=ROOT/'build/ReentryQA/Windows'
    cases=json.loads((args.candidates or ROOT/'results/reentry_candidates_4a05593a4282.json').read_text())
    manifest=json.loads(manifest_path.read_text())
    if cases['build_id']!=manifest['build_id'] or json.loads(world.read_text())['build_id']!=manifest['build_id']:
        raise RuntimeError('Access, mesh manifest and runtime world generations differ')
    if args.draft and (cases.get('manifest_sha256')!=digest(manifest_path) or cases.get('itinerary_sha256')!=digest(itinerary_path)):
        raise RuntimeError('Candidate access set was sampled from different source bytes')
    selected=[c for c in cases['candidates'] if c['station_m']==args.station]
    diagnostic=False
    if not selected and args.allow_geometric_diagnostic:
        selected=[c for c in cases.get('physical_diagnostic_candidates',[]) if c['station_m']==args.station]
        diagnostic=bool(selected)
    if len(selected)!=1:raise RuntimeError('Requested access is absent or ambiguous; a flagged access requires explicit diagnostic selection')
    candidate=selected[0]
    diagnostic=diagnostic or bool(candidate.get('requires_explicit_physical_diagnostic'))
    if diagnostic or candidate.get('requires_explicit_physical_diagnostic'):
        if not args.allow_geometric_diagnostic or not args.streetview_review:
            raise RuntimeError('A flagged access requires an explicit physical diagnostic and observed Street View access review')
        review=json.loads(args.streetview_review.read_text(encoding='utf-8'))
        if (review.get('station_m')!=args.station or review.get('build_id')!=manifest['build_id']
            or review.get('access_suitable_for_physical_diagnostic') is not True
            or abs(review.get('requested_wgs84',[0,0])[0]-candidate['latitude'])>1e-6
            or abs(review.get('requested_wgs84',[0,0])[1]-candidate['longitude'])>1e-6):
            raise RuntimeError('Street View review does not validate this diagnostic access')
    out=ROOT/'results/reentry_checks'/args.run_id
    if out.exists():raise RuntimeError('Preserve previous run; choose a fresh run id')
    if args.draft and qa.exists():raise RuntimeError('Preserve the existing candidate QA package; choose a fresh run id')
    out.mkdir(parents=True)
    protected=[ROOT/'parameters/current_road_design.json',ROOT/'Unreal/Content/Data/circuit_driving_world.json',
               ROOT/'Unreal/Content/Data/circuit_itinerary.json']
    protected_before={str(path):digest(path) for path in protected}
    if not qa.exists():shutil.copytree(production,qa)
    relative=Path('SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe')
    package_items=[relative,Path('SoffumbergoLab/Content/Paks/SoffumbergoLab-Windows.pak'),
                 Path('SoffumbergoLab/Content/Paks/SoffumbergoLab-Windows.ucas'),
                 Path('SoffumbergoLab/Content/Paks/SoffumbergoLab-Windows.utoc')]
    package_before={str(item):digest(production/item) for item in package_items}
    for item in package_items:
        if digest(production/item)!=digest(qa/item):raise RuntimeError('QA base differs from shipped game: '+str(item))
    profiles=json.loads((ROOT/'Unreal/Content/Data/profiles.json').read_text())
    profiles['REENTRY_QA']=pulse_profile(args.out_seconds,args.reverse_seconds,args.pulse_brake) if args.pulse else make_profile(candidate,args.reverse_scale)
    (out/'profiles.json').write_text(json.dumps(profiles))
    itinerary=json.loads(itinerary_path.read_text())
    itinerary['stops'][0]['position_cm']=candidate['center_UE_cm']
    itinerary['stops'][0]['arrival_yaw_rad']=candidate['yaw_rad']
    itinerary['diagnostic_initial_spawn_only']=True
    (out/'circuit_itinerary.json').write_text(json.dumps(itinerary))
    response=out/'pak_response.txt'
    response.write_text('\n'.join('"'+str(out/name)+'" "../../../SoffumbergoLab/Content/Data/'+name+'"'
                                 for name in ['profiles.json','circuit_itinerary.json']))
    # Create in the fresh evidence folder; preserve each pak before replacing
    # the one QA-only override between finished trials. Production is untouched.
    patch=qa/'SoffumbergoLab/Content/Paks/ReentryQA_P.pak'
    saved_patch=out/'ReentryQA_P.pak'
    with (out/'create_pak.log').open('w') as log:
        subprocess.run([str(PAK),str(saved_patch),'-Create='+str(response)],stdout=log,stderr=subprocess.STDOUT,
                       check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    shutil.copyfile(saved_patch,patch)
    exe=qa/relative
    command=[str(exe),'/Game/Maps/CircuitoGuidabile','-game','-unattended','-nosplash','-nosound',
             '-LabTest=REENTRY_QA','-CircuitTestStop=0','-LabRunId='+args.run_id,
             '-LabOutput='+str(out),'-abslog='+str(out/'engine.log'),'-LabUncapped','-pak.AllowMissingUToc']
    if args.render:command+=['-RenderOffscreen','-windowed','-ForceRes','-ResX=3840','-ResY=2160','-LabPreset=C','-LabCapture','-LabCaptureAt=15']
    else:command+=['-nullrhi','-UseFixedTimeStep','-FPS=120']
    if args.max_fps is not None:command+=['-ExecCmds=t.MaxFPS '+str(args.max_fps)]
    launch={'command':command,'candidate':candidate,'world_build_id':manifest['build_id'],
            'world_sha1':hashlib.sha1(world.read_bytes()).hexdigest(),
            'game_binary_sha256':digest(exe),'diagnostic_patch_sha256':digest(patch),
            'profiles_sha256':digest(out/'profiles.json'),'qa_itinerary_sha256':digest(out/'circuit_itinerary.json'),
            'candidate_draft':str(args.draft.resolve()) if args.draft else None,
            'access_manifest_sha256':digest(manifest_path),'access_cases_sha256':digest(args.candidates or ROOT/'results/reentry_candidates_4a05593a4282.json'),
            'conservative_grade_screen_failed':diagnostic,
            'streetview_review':str(args.streetview_review.resolve()) if args.streetview_review else None,
            'streetview_review_sha256':digest(args.streetview_review) if args.streetview_review else None,
            'source_package':str(production),'isolated_qa_package':str(qa),
            'protected_files_before':protected_before,'source_package_before':package_before,
            'production_package_changed':False,'physics_source_changed':False,
            'scope':'initial diagnostic spawn, force-driven road-to-meadow and reverse reentry; never a full lap',
            'rendering':args.render,'prepared_unix':time.time()}
    (out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
    if args.prepare_only:
        print(json.dumps({'prepared':str(out)}));return
    launch['started_unix']=time.time();(out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
    with (out/'console.log').open('w') as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        launch['native_pid']=process.pid
        (out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
        while True:
            try:
                native_code=process.wait(timeout=300)
                break
            except subprocess.TimeoutExpired:
                # An observation interval must not kill or restart the test.
                launch.setdefault('observation_timeouts_unix',[]).append(time.time())
                (out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
    ended=time.time()
    with (out/'concurrent_interval.json').open('w') as f:json.dump({'started_unix':launch['started_unix'],'ended_unix':ended,
        'reason':'separate QA process; record overlap when interpreting full-lap frame times'},f,indent=2)
    if native_code:raise RuntimeError('Native test failed; inspect engine log')
    meta=json.loads((out/(args.run_id+'.json')).read_text(encoding='utf-8-sig'))
    with (out/(args.run_id+'.csv')).open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    xy=np.array([[float(r['x_m']),-float(r['y_m'])] for r in rows])*100
    yaw=-np.array([float(r['yaw_rad']) for r in rows])
    center=np.asarray(candidate['center_UE_cm'])[:2]
    road=RoadSurface(manifest,include_shoulders=True)
    allowed=road.local_drivable_polygon(center,25).buffer(2)
    rectangles=[]
    for point,angle in zip(xy,yaw):
        co,si=math.cos(angle),math.sin(angle)
        rectangles.append(shapely.Polygon(np.array([[-215,-105],[215,-105],[215,105],[-215,105]])@np.array([[co,si],[-si,co]])+point))
    on=shapely.covers(allowed,rectangles);off=shapely.disjoint(allowed,rectangles)
    asphalt=RoadSurface(manifest)
    neighborhood=shapely.box(center[0]-2500,center[1]-2500,center[0]+2500,center[1]+2500)
    asphalt_polygon=shapely.union_all(asphalt.polygons[asphalt.tree.query(neighborhood,predicate='intersects')]).buffer(2)
    on_asphalt=shapely.covers(asphalt_polygon,rectangles)
    times=np.array([float(r['time_s']) for r in rows])
    contacts=np.array([[int(float(r[k+'_contact'])) for k in ['FL','FR','RL','RR']] for r in rows]).sum(axis=1)
    speed=np.linalg.norm([[float(r[k]) for k in ['vx_m_s','vy_m_s','vz_m_s']] for r in rows],axis=1)
    throttle=np.array([float(r['throttle']) for r in rows])
    excursion=(xy-center)@np.asarray(candidate['forward_UE_xy'])/100
    active=times>2
    final=times>times[-1]-2
    off_ids=np.flatnonzero(off)
    return_ids=np.flatnonzero(on&(times>times[off_ids[-1]])) if len(off_ids) else np.array([],int)
    # Check the actual injected curve and initial spawn, not merely pak filenames.
    keys=np.asarray(profiles['REENTRY_QA']['keys'])
    input_error=max(float(np.max(np.abs(np.array([float(r[name]) for r in rows])-np.interp(times,keys[:,0],keys[:,j]))))
                    for j,name in enumerate(['throttle','brake','steering_input'],1))
    # Telemetry samples are stamped before the subsequent Elapsed increment.
    checks={'native_completed':meta['status']=='executed' and meta['simulated_s']>=profiles['REENTRY_QA']['duration_s'],
            'requested_rendering_mode':bool(meta.get('RHI')) and (meta['RHI']!='Null')==args.render,
            'actual_world_generation':meta['road_world_build_id']==manifest['build_id'],
            'actual_world_payload':meta['road_world_data_sha1']==launch['world_sha1'],
            'source_package_unchanged':all(digest(production/item)==value for item,value in package_before.items()),
            'active_files_unchanged':all(digest(path)==value for path,value in protected_before.items()),
            'requested_fps_limit':args.max_fps is None or abs(meta.get('graphics_settings',{}).get('t.MaxFPS',-1)-args.max_fps)<.01,
            'same_game_binary':digest(exe)==digest(production/relative),
            'actual_initial_spawn':float(np.linalg.norm(xy[0]-center))<5,
            'actual_input_curve':input_error<.002,
            'complete_vehicle':meta['final_assets_loaded'] and meta['mass_measurement_valid'] and abs(meta['mass_kg']-1605)<.1 and not meta['physics_disabled_for_graphics'],
            'no_reset':meta['user_resets']==0,'startup_wait_only':meta['terrain_wait_episodes']<=1,
            'fully_off_built_road':bool(np.any(off&active)),
            'returned_after_excursion':bool(len(return_ids)),
            'final_body_on_road':bool(np.all(on[final])),
            'final_body_fully_on_asphalt':bool(np.all(on_asphalt[final])),
            'final_stationary':float(speed[final].max())<.12,
            'contacts_preserved':bool(np.all(contacts[active]>=3)),
            'forward_and_reverse':bool(throttle.max()>.05 and throttle.min()<-.05),
            'upright':max(abs(float(r['roll_rad'])) for r in rows)<math.radians(25),
            'viewport_matches_requested_mode':not args.render or meta.get('viewport_width')==3840 and meta.get('viewport_height')==2160}
    report={'passed':all(checks.values()),'checks':checks,'world_build_id':manifest['build_id'],
            'rendering':args.render,'RHI':meta.get('RHI'),'max_excursion_m':float(excursion.max()),'final_excursion_m':float(excursion[-1]),
            'off_built_road_sample_count':int(off.sum()),'returned_sample_count':int(len(return_ids)),
            'final_asphalt_body_samples':int(np.count_nonzero(on_asphalt[final])),
            'final_samples':int(np.count_nonzero(final)),
            'min_contacts_after_settle':int(contacts[active].min()),'final_speed_max_m_s':float(speed[final].max()),
            'input_curve_max_error':input_error,'game_binary_sha256':launch['game_binary_sha256'],
            'scope':launch['scope'],'limitations':'One selected feasible meadow access; no claim that every roadside is traversable. Does not prove a full rendered lap.'}
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
