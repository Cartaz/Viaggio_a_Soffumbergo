"""Observe all streamed PCG instances and compare to accepted Editor snapshots."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import time
import _winapi

ROOT=Path(__file__).resolve().parents[1]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def canonical(rows,zero_equivalence=False):
    result=[]
    for row in rows:
        values=[round(float(x),4) for x in row[1:]]
        if not all(math.isfinite(x) for x in values):raise RuntimeError('Nonfinite runtime transform')
        if zero_equivalence:values=[0.0 if x==0 else x for x in values]
        result.append([row[0],*values])
    result.sort();return hashlib.sha256(json.dumps(result,separators=(',',':')).encode()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--draft',type=Path,required=True);p.add_argument('--generation-journal',type=Path,required=True)
    p.add_argument('--run-id',required=True);p.add_argument('--packaged',action='store_true')
    p.add_argument('--runtime-identity',type=Path,help='Explicit source/binary pins for a content candidate; default is runtime_revision.json')
    args=p.parse_args()
    if not re.fullmatch('[a-z0-9_]+',args.run_id):raise ValueError('Unsafe run id')
    draft=args.draft.resolve();identity_path=(args.runtime_identity or draft/'runtime_revision.json').resolve()
    revision=json.loads(identity_path.read_text())
    imported=json.loads((draft/'import_report.json').read_text());assert imported['all_imported']
    manifest=json.loads(Path(imported['manifest']).read_text());build=manifest['build_id']
    generation=json.loads(args.generation_journal.read_text());assert generation['all_imported'] and not generation.get('error')
    generation_draft=args.generation_journal.resolve().parent
    generation_import=json.loads((generation_draft/'import_report.json').read_text());original=json.loads(Path(generation_import['manifest']).read_text())
    expected_tiles={t['id']:t for t in original['tiles']}
    for tile in manifest['tiles']:
        base=expected_tiles[tile['id']]
        assert tile['height_sha256']==base['height_sha256'] and tile['holes_sha256']==base['holes_sha256']
    collision={name:b['collision'] for b in manifest['vegetation']['config']['branches'] for name in b['meshes']}
    world=draft/'circuit_driving_world.json';world_sha1=hashlib.sha1(world.read_bytes()).hexdigest()
    assert revision['build_id']==build
    if 'world_sha256' in revision:assert revision['world_sha256']==sha(world)
    if 'itinerary_sha256' in revision:assert revision['itinerary_sha256']==sha(draft/'circuit_itinerary.json')
    out=ROOT/'results/vegetation_census'/args.run_id
    if out.exists():raise RuntimeError('Preserve previous census')
    out.mkdir(parents=True)
    if args.packaged:
        pack=json.loads((draft/'candidate_packaging_report.json').read_text());assert pack['packaged']
        assert pack['world_sha256']==sha(world)
        binary=Path(pack['archive'])/'Windows/SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe'
        assert sha(binary)==pack['game_binary_sha256'];command=[str(binary)]
    else:
        assert sha(ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoLab.dll')==revision['editor_binary_sha256']
        assert all(sha(path)==expected for path,expected in revision['source_sha256'].items())
        original_project=ROOT/'Unreal';qa=out/'UnrealProject';qa.mkdir()
        shutil.copyfile(original_project/'SoffumbergoLab.uproject',qa/'SoffumbergoLab.uproject');shutil.copytree(original_project/'Config',qa/'Config')
        (qa/'Binaries/Win64').mkdir(parents=True)
        for file in (original_project/'Binaries/Win64').iterdir():
            if file.suffix in ['.dll','.modules','.target']:shutil.copyfile(file,qa/'Binaries/Win64'/file.name)
        (qa/'Content').mkdir()
        for file in (original_project/'Content').iterdir():
            if file.name=='Data':shutil.copytree(file,qa/'Content/Data')
            elif file.is_dir():_winapi.CreateJunction(str(file),str(qa/'Content'/file.name))
            else:shutil.copyfile(file,qa/'Content'/file.name)
        for file in [world,draft/'circuit_itinerary.json']:shutil.copyfile(file,qa/'Content/Data'/file.name)
        binary=qa/'Binaries/Win64/UnrealEditor-SoffumbergoLab.dll'
        command=['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe',str(qa/'SoffumbergoLab.uproject')]
    command+=['/Game/Maps/CircuitoGuidabile','-game','-nullrhi','-unattended','-nosplash','-nosound','-CircuitVegetationSurvey',
        '-UseFixedTimeStep','-FPS=120','-LabOutput='+str(out),'-LabRunId='+args.run_id,'-abslog='+str(out/'engine.log')]
    guard_paths=[ROOT/'parameters/current_road_design.json',ROOT/'Unreal/Content/Data/circuit_driving_world.json',ROOT/'Unreal/Content/Data/circuit_itinerary.json',ROOT/'Unreal/Content/Maps/CircuitoGuidabile.umap']
    guard_paths += [ROOT/'Unreal/Content'/(t['map'].removeprefix('/Game/')+'.umap') for t in manifest['tiles']]
    before={str(path):sha(path) for path in guard_paths}
    started=time.time();launch={'build_id':build,'revision':revision['revision'],'started_unix':started,'command':command,
        'runtime_identity':str(identity_path),'runtime_identity_sha256':sha(identity_path),
        'runtime_binary_sha256':sha(binary),'world_data_sha1':world_sha1,'packaged':args.packaged,'generation_journal_sha256':sha(args.generation_journal),
        'protected_before':before,'rendering':False}
    (out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
    with (out/'console.log').open('x') as log:
        process=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        launch['native_pid']=process.pid;(out/'launch_manifest.json').write_text(json.dumps(launch,indent=2))
        print('PCG_CENSUS_NATIVE_PID '+str(process.pid),flush=True);code=process.wait()
    report={'build_id':build,'revision':revision['revision'],'packaged':args.packaged,'rendering':False,'passed':False,'native_exit_code':code,'tiles':[]}
    try:
        native_path=out/'circuit_vegetation_survey.json';assert native_path.stat().st_mtime>=started
        native=json.loads(native_path.read_text(encoding='utf-8-sig'))
        assert code==0 and native['native_readback_passed'] and native['completed'] and native['expected_tiles']==native['checked_tiles']==113
        assert native['build_id']==build and native['world_data_sha1']==world_sha1 and native['RHI']=='Null'
        wanted={t['id'] for t in manifest['tiles']};assert {t['tile'] for t in native['tiles']}==wanted
        total=0;strict=0
        for tile in native['tiles']:
            name=tile['tile'];snapshot=generation['tiles'].get(name,{}).get('reload_snapshot',{'counts':{},'instances':0})
            expected_rows=json.loads(gzip.decompress((generation_draft/('pcg_instances_'+name+'.json.gz')).read_bytes())) if name in generation['tiles'] else []
            assert len(expected_rows)==snapshot['instances']
            if name in generation['tiles']:assert canonical(expected_rows)==snapshot['sha256']
            data=json.loads((out/tile['rows_file']).read_text(encoding='utf-8-sig'));observed=data['instances']
            counts={k:int(v) for k,v in tile['counts'].items()}
            actual=canonical(observed);expected=canonical(expected_rows)
            exact=actual==expected;equivalent=canonical(observed,True)==canonical(expected_rows,True)
            components_ok=True
            for component in tile['components']:
                key=component['mesh_name'];solid=collision[key]
                source_asset=generation['mesh_info'][key]['asset']
                components_ok &= component['mesh'].split('.')[0]==source_asset and not component['simulating_physics']
                components_ok &= component['collision_enabled']==(3 if solid else 0)
                if solid:components_ok &= component['convex_hulls']==1 and component['visibility_response']==2
            passed=tile['native_readback_passed'] and tile['rows_saved'] and len(observed)==tile['instances']==snapshot['instances'] and counts==snapshot['counts'] and equivalent and components_ok
            report['tiles'].append({'tile':name,'passed':bool(passed),'expected_instances':snapshot['instances'],'observed_instances':tile['instances'],
                'counts_match':counts==snapshot['counts'],'strict_round4_sort_sha256_match':exact,'signed_zero_equivalent_round4_sort_match':equivalent,
                'mesh_assets_and_collision_settings_match':bool(components_ok),'observed_rows_sha256':actual,'expected_rows_sha256':expected})
            total+=tile['instances'];strict+=int(exact)
        distant=native['distant_terrain'];expected_far={r['id']:r for r in manifest['distant_terrain']['records']}
        assert distant['passed'] and distant['expected']==distant['loaded_levels']==113
        far_ok=(len(distant['meshes'])==113
            and {item['tile'] for item in distant['meshes']}==set(expected_far)
            and all(item['mesh'].split('.')[0]==expected_far[item['tile']]['asset'] for item in distant['meshes']))
        buffers_proven=far_ok and all(item['lod0_triangles_if_resident']==expected_far[item['tile']]['triangles'] for item in distant['meshes'])
        report.update(total_instances=total,expected_instances=sum(t['reload_snapshot']['instances'] for t in generation['tiles'].values()),
            strict_hash_matching_tiles=strict,signed_zero_normalization_only=True,
            signed_zero_only_matching_tiles=sum(not t['strict_round4_sort_sha256_match'] and t['signed_zero_equivalent_round4_sort_match'] for t in report['tiles']),
            far_assets_match=far_ok,
            far_lod0_triangles_if_resident=distant['lod0_triangles_if_resident'],
            far_runtime_lod0_section_counts_match=buffers_proven,
            far_runtime_lod0_section_counts_available=all(item['lod0_triangles_if_resident']>0 for item in distant['meshes']),
            far_runtime_lod_buffers_proven=False,
            far_readback_scope='UStaticMesh::GetNumTriangles sums LOD section counts; no raw vertex/index-buffer bytes or GPU residency verified.',
            protected_files_unchanged=all(sha(path)==expected for path,expected in before.items()),native_report=str(native_path),
            scope='All native saved vegetation transforms rounded/sorted as in the original Editor snapshot; signed-zero equivalence separately recorded. No driving, regeneration, pixels or GPU performance acceptance.')
        report['passed']=all(t['passed'] for t in report['tiles']) and total==report['expected_instances'] and far_ok and report['protected_files_unchanged']
    except BaseException as e:report['error']=repr(e)
    report['ended_unix']=time.time();(out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='tiles'},indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
