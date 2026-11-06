"""Render three real vehicle views and configured keys at each observed roadside.

Only a separate QA package's diagnostic initial spawn is overridden. The car,
physics, road, terrain and anthropic assets are exactly the candidate export.
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
import struct
import sys
import time
import _winapi
import numpy as np
from road_surface import RoadSurface

ROOT=Path(__file__).resolve().parents[1]
PAK=Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealPak.exe')


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--draft',type=Path,required=True)
    p.add_argument('--attempt',default='v1')
    p.add_argument('--editor',action='store_true',help='Check current Editor code in an isolated project before export')
    p.add_argument('--control',help='Optional single observed control; never a full gallery claim')
    p.add_argument('--review-controls',type=Path,help='Separate source-backed diagnostic viewpoints; never changes world geometry')
    p.add_argument('--reverse-control-heading',action='store_true',help='Single-control diagnostic initial heading reversed to inspect a terminal from the open approach')
    p.add_argument('--background-log',type=Path)
    p.add_argument('--diagnostic-lod0',action='store_true',help='Controlled diagnostic only: force native LOD0, never a performance acceptance')
    p.add_argument('--diagnostic-serial-compute',action='store_true',help='Controlled GPU diagnostic only: r.RDG.AsyncCompute=0; no production setting change')
    p.add_argument('--diagnostic-static-sky',action='store_true',help='Controlled GPU diagnostic only: capture the existing sky light once instead of every frame')
    p.add_argument('--diagnostic-sky-capture-off',action='store_true',help='Disable real-time sky capture in engine startup configuration; retain the normal one-time sky light capture')
    args=p.parse_args()
    if args.diagnostic_static_sky and args.diagnostic_sky_capture_off:p.error('Use one sky diagnostic at a time')
    if args.reverse_control_heading and not args.control:p.error('A reversed diagnostic heading requires a single control')
    if args.background_log:
        sys.stdout=args.background_log.open('x',buffering=1);sys.stderr=sys.stdout
    if not re.fullmatch('[a-z0-9_]+',args.attempt):p.error('Use a simple unique attempt name')
    draft=args.draft.resolve();prepared=json.loads((draft/'structure_preparation.json').read_text())
    build=prepared['build_id'];m=json.loads(Path(prepared['manifest']).read_text())
    review_controls=None
    if args.review_controls:
        review_controls=json.loads(args.review_controls.read_text(encoding='utf-8'))
        if review_controls.get('build_id')!=build:raise ValueError('Diagnostic viewpoints must match the selected world')
        controls=review_controls['controls']
        if not controls or len({c['id'] for c in controls})!=len(controls):raise ValueError('Unique diagnostic viewpoints required')
        for c in controls:
            if not re.fullmatch('[a-z0-9_]+',c['id']):raise ValueError('Unsafe diagnostic viewpoint id')
            if len(c['center_UE_xy_m'])!=2 or not all(math.isfinite(x) for x in c['center_UE_xy_m']):raise ValueError('Finite source location required')
            source=ROOT/c['source_review']
            if not source.is_file():raise ValueError('Diagnostic viewpoint requires a recorded source review')
            if 'heading_degrees' in c:raise ValueError('Photo headings cannot set a moving key-test spawn. Use source_heading_degrees for reference and reverse_itinerary_heading for the opposite road direction.')
            if 'reverse_itinerary_heading' in c and not isinstance(c['reverse_itinerary_heading'],bool):raise ValueError('Road-direction reversal must be explicit boolean')
    world=draft/'circuit_driving_world.json';itinerary_path=draft/'circuit_itinerary.json'
    if args.editor:
        imported=json.loads((draft/'import_report.json').read_text())
        if not imported['all_imported'] or imported['build_id']!=build:
            raise RuntimeError('Matching native import is required before the Editor gallery')
    else:
        pack=json.loads((draft/'candidate_packaging_report.json').read_text())
        if not pack['packaged'] or pack['world_sha256']!=sha(world) or pack['itinerary_sha256']!=sha(itinerary_path):
            raise RuntimeError('Candidate export differs from the selected data')
    original=ROOT/'Unreal' if args.editor else Path(pack['archive'])/'Windows'
    qa=ROOT/'build/StructureGalleryQA'/build/args.attempt/('UnrealProject' if args.editor else 'Windows')
    out=ROOT/'results/structure_gallery'/build/args.attempt
    if out.exists() or qa.exists():raise RuntimeError('Preserve earlier gallery; inspect its actual outcome')
    out.mkdir(parents=True)
    if args.editor:
        qa.mkdir(parents=True)
        shutil.copyfile(original/'SoffumbergoLab.uproject',qa/'SoffumbergoLab.uproject')
        shutil.copytree(original/'Config',qa/'Config')
        shutil.copytree(original/'Binaries',qa/'Binaries',ignore=shutil.ignore_patterns('*.pdb'))
        (qa/'Content').mkdir()
        for item in (original/'Content').iterdir():
            if item.name=='Data':shutil.copytree(item,qa/'Content/Data')
            elif item.is_dir():_winapi.CreateJunction(str(item),str(qa/'Content'/item.name))
            elif item.is_file():shutil.copyfile(item,qa/'Content'/item.name)
        for path in [world,itinerary_path]:shutil.copyfile(path,qa/'Content/Data'/path.name)
        relatives=[Path('Binaries/Win64/UnrealEditor-SoffumbergoLab.dll')]
    else:
        shutil.copytree(original,qa)
        relatives=[Path('SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe')]+[
            Path('SoffumbergoLab/Content/Paks/SoffumbergoLab-Windows.'+suffix) for suffix in ['pak','utoc','ucas']]
    base={str(path):sha(original/path) for path in relatives}
    if not all(sha(qa/path)==value for path,value in base.items()):raise RuntimeError('Gallery copy differs from candidate')
    surface=RoadSurface(m);itinerary=json.loads(itinerary_path.read_text());points=np.asarray(itinerary['points_cm'])
    report={'build_id':build,'started_unix':time.time(),'source_package_sha256':base,'cases':[],
            'diagnostic_force_lod0':args.diagnostic_lod0,
            'diagnostic_serial_compute':args.diagnostic_serial_compute,
            'diagnostic_static_sky':args.diagnostic_static_sky,
            'diagnostic_sky_capture_off':args.diagnostic_sky_capture_off,
            'runtime':'Editor' if args.editor else 'Windows package','single_control':args.control,
            'diagnostic_initial_heading_reversed':args.reverse_control_heading,
            'passed':False,'camera_visibility_reviewed':False,'scope':'Three native views plus short configured-key movements at six observed roadside controls; no full-lap claim'}
    if review_controls:
        report.update({'review_controls':str(args.review_controls.resolve()),'review_controls_sha256':sha(args.review_controls),
                       'source_review_sha256':{c['source_review']:sha(ROOT/c['source_review']) for c in controls},
                       'scope':'Source-backed diagnostic viewpoints with three native views and configured keys. No full-gallery, world geometry or full-lap acceptance.'})
    report_path=out/'report.json'
    report_path.write_text(json.dumps(report,indent=2))
    if review_controls is None:controls=m['roadside_structures']['config']['controls']
    if args.control:
        controls=[c for c in controls if c['id']==args.control]
        if len(controls)!=1:raise ValueError('Unknown observed control')
    for control in controls:
        case=out/control['id'];case.mkdir()
        run='gallery_'+control['id']
        center=np.asarray(control['center_UE_xy_m'])*100
        i=int(np.argmin(np.linalg.norm(points[:,:2]-center,axis=1)))
        position=points[i].copy();z,distance=surface.sample(position[:2]);position[2]=z[0]
        if distance[0]>.01:raise RuntimeError('Gallery spawn is outside candidate asphalt')
        direction=points[min(i+1,len(points)-1),:2]-points[max(i-1,0),:2]
        yaw=math.atan2(direction[1],direction[0])
        if args.reverse_control_heading != control.get('reverse_itinerary_heading',False):yaw=math.atan2(math.sin(yaw+math.pi),math.cos(yaw+math.pi))
        local=json.loads(itinerary_path.read_text());local['stops'][0]['position_cm']=position.tolist()
        local['stops'][0]['arrival_yaw_rad']=yaw;local['diagnostic_initial_spawn_only']=True
        override=case/'circuit_itinerary.json';override.write_text(json.dumps(local))
        if args.editor:
            shutil.copyfile(override,qa/'Content/Data/circuit_itinerary.json')
            command=[str(PAK.parent/'UnrealEditor-Cmd.exe'),str(qa/'SoffumbergoLab.uproject')]
        else:
            response=case/'pak_response.txt'
            response.write_text('"'+str(override)+'" "../../../SoffumbergoLab/Content/Data/circuit_itinerary.json"')
            patch=case/'StructureGalleryQA_P.pak'
            with (case/'create_pak.log').open('w') as log:
                subprocess.run([str(PAK),str(patch),'-Create='+str(response)],stdout=log,stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW,check=True)
            shutil.copyfile(patch,qa/'SoffumbergoLab/Content/Paks/StructureGalleryQA_P.pak')
            command=[str(qa/relatives[0])]
        command+=['/Game/Maps/CircuitoGuidabile','-game','-unattended','-nosplash','-nosound',
            '-LabInputCheck','-CircuitTestStop=0','-pak.AllowMissingUToc','-RenderOffscreen','-windowed','-ForceRes',
            '-ResX=3840','-ResY=2160','-LabPreset=C','-ExecCmds=t.MaxFPS 60',
            '-LabRunId='+run,'-LabOutput='+str(case),'-abslog='+str(case/'engine.log')]
        exec_commands=['t.MaxFPS 60']
        if args.diagnostic_lod0:exec_commands.append('r.ForceLOD 0')
        if args.diagnostic_serial_compute:exec_commands.append('r.RDG.AsyncCompute 0')
        if args.diagnostic_sky_capture_off:
            exec_commands.append('r.SkyLight.RealTimeReflectionCapture 0')
            command.append('-ini:Engine:[SystemSettings]:r.SkyLight.RealTimeReflectionCapture=0')
        command[command.index('-ExecCmds=t.MaxFPS 60')]='-ExecCmds='+','.join(exec_commands)
        if args.diagnostic_static_sky:command.append('-LabStaticSky')
        launch={'command':command,'build_id':build,'initial_position_cm':position.tolist(),'yaw_rad':yaw,
            'initial_heading_method':'Actual itinerary tangent; optional 180 degree reversal. Source photograph heading never rotates the moving car across the road.',
            'source_heading_degrees':control.get('source_heading_degrees'),
            'runtime_world_sha1':hashlib.sha1(world.read_bytes()).hexdigest(),'qa_itinerary_sha256':sha(override),
            'native_binary_sha256':base[str(relatives[0])],'started_unix':time.time()}
        (case/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
        with (case/'console.log').open('w') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
        meta_path=case/(run+'.json');input_path=case/(run+'_input.json')
        if any(not path.exists() or path.stat().st_mtime<launch['started_unix'] for path in [meta_path,input_path]):
            native_log=(case/'engine.log').read_text(encoding='utf-8',errors='replace')
            failure={'control':control['id'],'native_exit_code':result.returncode,'fresh_telemetry_missing':True,
                     'gpu_device_hung':'DXGI_ERROR_DEVICE_HUNG' in native_log,'ended_unix':time.time(),
                     'acceptance':False,'source_package_unchanged':all(sha(original/path)==value for path,value in base.items())}
            (case/'interruption.json').write_text(json.dumps(failure,indent=2))
            raise RuntimeError('Missing fresh gallery telemetry for '+control['id'])
        meta=json.loads(meta_path.read_text(encoding='utf-8-sig'));keys=json.loads(input_path.read_text(encoding='utf-8-sig'))
        with (case/(run+'.csv')).open(encoding='utf-8-sig') as f:first=next(csv.DictReader(f))
        actual=np.array([float(first['x_m']),-float(first['y_m'])])*100
        shots={}
        for name in ['external','cabin','coffa']:
            filename=run+'_camera_'+name+'.png'
            # Some Windows engine configurations route captures to the game's
            # private screenshot directory even with an absolute request name.
            candidates=[case/filename,qa/'private/screenshots'/filename,
                        qa/'SoffumbergoLab/Saved/Screenshots/Windows'/filename]
            if args.editor:candidates.append(qa.parent/'private/screenshots'/filename)
            fresh=[path for path in candidates if path.exists() and path.stat().st_mtime>=launch['started_unix']]
            if not fresh:fresh=[path for path in qa.rglob(filename) if path.stat().st_mtime>=launch['started_unix']]
            shots[name]=fresh[0] if fresh else case/filename
        image_sizes={}
        for name,path in shots.items():
            if path.exists():
                with path.open('rb') as f:header=f.read(24)
                if header[:8]==b'\x89PNG\r\n\x1a\n':image_sizes[name]=list(struct.unpack('>II',header[16:24]))
        checks={'native_exit':result.returncode==0,'configured_input_bindings':keys['passed'],
            'actual_world_generation':meta['road_world_build_id']==build,
            'actual_world_payload':meta['road_world_data_sha1']==launch['runtime_world_sha1'],
            'initial_spawn':float(np.linalg.norm(actual-position[:2]))<5,
            'full_real_vehicle':meta['final_assets_loaded'] and meta['mass_measurement_valid'] and abs(meta['mass_kg']-1605)<.1 and not meta['physics_disabled_for_graphics'],
            'one_requested_reset':meta['user_resets']==1,'startup_wait_only':meta['terrain_wait_episodes']<=1,
            'actual_4k':meta.get('viewport_width')==3840 and meta.get('viewport_height')==2160,
            'actual_fps_limit':abs(meta.get('graphics_settings',{}).get('t.MaxFPS',-1)-60)<.01,
            'fresh_three_views':all(path.exists() and path.stat().st_mtime>=launch['started_unix'] for path in shots.values()),
            'three_actual_4k_images':len(image_sizes)==3 and all(size==[3840,2160] for size in image_sizes.values())}
        if args.diagnostic_lod0:
            checks['native_lod_override_applied']='r.ForceLOD = "0"' in (case/'engine.log').read_text(encoding='utf-8',errors='replace')
        native_log=(case/'engine.log').read_text(encoding='utf-8',errors='replace')
        if args.diagnostic_serial_compute:
            checks['native_serial_compute_override_applied']='r.RDG.AsyncCompute = "0"' in native_log
        if args.diagnostic_static_sky:
            checks['native_static_sky_applied']=meta.get('diagnostic_static_sky') is True and meta.get('sky_light_count',0)>0 and meta.get('realtime_sky_light_count',-1)==0
        if args.diagnostic_sky_capture_off:
            checks['native_sky_capture_disabled_from_startup']='Set CVar [[r.SkyLight.RealTimeReflectionCapture:0]]' in native_log and meta.get('sky_light_count',0)>0 and meta.get('realtime_sky_light_count',-1)==0 and meta.get('diagnostic_static_sky') is False
        checks['no_material_compilation_fallback']='Failed to compile Material' not in native_log
        entry={'control':control['id'],'checks':checks,'passed':all(checks.values()),
            'screenshots':{k:str(v) for k,v in shots.items()},'image_sizes':image_sizes,'camera_visibility_reviewed':False}
        report['cases'].append(entry);report_path.write_text(json.dumps(report,indent=2))
        if not entry['passed']:raise RuntimeError('Gallery runtime checks failed for '+control['id'])
    report['source_package_unchanged']=all(sha(original/path)==value and sha(qa/path)==value for path,value in base.items())
    report['passed']=len(report['cases'])==len(controls) and all(c['passed'] for c in report['cases']) and report['source_package_unchanged']
    report['full_six_control_gallery']=not args.control and review_controls is None and report['passed']
    report['ended_unix']=time.time();report_path.write_text(json.dumps(report,indent=2))
    print(json.dumps({'passed':report['passed'],'build_id':build,'cases':len(report['cases']),'camera_visibility_reviewed':False}))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
