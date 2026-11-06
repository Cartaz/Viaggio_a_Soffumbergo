"""Clone proven levels and replace only their earth-overlay actor in Unreal."""
import hashlib
import json
import os
from pathlib import Path
import time
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve().parent
manifest=Path(os.environ['SOFFUMBERGO_SHOULDER_MANIFEST'])
m=json.loads(manifest.read_text());repair=m['shoulder_repair'];build=m['build_id']
draft=ROOT/'results/road_drafts'/build
parent_import=json.loads((Path(repair['parent_draft'])/'import_report.json').read_text())
if not parent_import['all_imported'] or parent_import['build_id']!=repair['parent_build_id']:
    raise RuntimeError('Matching native parent import required')
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assets=unreal.EditorAssetLibrary


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


changed=[t for t in m['tiles'] if t.get('shoulder_parent_map')]
protected=[ROOT/'parameters/current_road_design.json',ROOT/'Unreal/Content/Data/circuit_driving_world.json',
    ROOT/'Unreal/Content/Data/circuit_itinerary.json',ROOT/'Unreal/Content/Maps/CircuitoGuidabile.umap']
protected += [ROOT/'Unreal/Content'/(t['shoulder_parent_map'].removeprefix('/Game/')+'.umap') for t in changed]
before={str(p):sha(p) for p in protected}
attempt=os.environ.get('SOFFUMBERGO_SHOULDER_ATTEMPT','v1')
if not attempt.replace('_','').isalnum():raise ValueError('Invalid import attempt')
journal_path=draft/('shoulder_native_import_'+attempt+'.json')
if journal_path.exists():raise RuntimeError('Preserve earlier native import evidence')
resume_path=os.environ.get('SOFFUMBERGO_SHOULDER_RESUME_JOURNAL');tracked={}
if resume_path:
    resume=json.loads(Path(resume_path).read_text())
    if resume['build_id']!=build or resume['protected_before']!=before:
        raise RuntimeError('Resume evidence differs from protected parent state')
    tracked=resume['tiles']
journal={'build_id':build,'parent_build_id':repair['parent_build_id'],'started_unix':time.time(),
    'protected_before':before,'tiles':{},'all_imported':False,'resume_journal':resume_path}


def save():journal_path.write_text(json.dumps(journal,indent=2))


def work():
    try:
        for tile in changed:
            if assets.does_asset_exist(tile['map']):
                prior=tracked.get(tile['id'])
                if not prior or prior['map']!=tile['map'] or prior['parent_map']!=tile['shoulder_parent_map']:
                    raise RuntimeError('Preserving untracked existing map '+tile['map'])
                levels.load_level(tile['map'])
            elif not levels.new_level_from_template(tile['map'],tile['shoulder_parent_map']):
                raise RuntimeError('Failed to clone '+tile['id'])
            record={'parent_map':tile['shoulder_parent_map'],'map':tile['map'],'saved_complete':False,'meshes':[],'collision_probes':[]}
            journal['tiles'][tile['id']]=record;save();targets=[]
            for info in [r for r in repair['records'] if r['tile']==tile['id']]:
                if sha(info['source'])!=info['sha256']:raise RuntimeError('Overlay source changed')
                old=[a for a in actors.get_all_level_actors() if a.get_actor_label()==info['id']]
                if len(old)!=1 or not old[0].actor_has_tag('RoadShoulder'):
                    raise RuntimeError('Parent shoulder actor is ambiguous '+info['id'])
                actors.destroy_actor(old[0])
                mesh=unreal.LidarTerrainLibrary.create_circuit_mesh(info['source'],info['asset'],'/Game/World/Materials/M_Road_shoulder')
                if mesh is None:raise RuntimeError('Overlay creation failed')
                assets.save_loaded_asset(mesh)
                actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*info['location_cm']))
                component=actor.get_component_by_class(unreal.StaticMeshComponent);component.set_static_mesh(mesh)
                component.set_collision_profile_name('BlockAll');component.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
                actor.set_actor_label(info['id']);actor.set_editor_property('tags',['RoadShoulder'])
                record['meshes'].append(info['id']);targets.append((actor,info))
            yield
            components=[a.get_component_by_class(unreal.StaticMeshComponent) for a in actors.get_all_level_actors() if isinstance(a,unreal.StaticMeshActor)]
            states=[c.get_collision_enabled() for c in components]
            try:
                for c in components:c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                terrain=json.loads(unreal.LidarTerrainLibrary.verify_lidar_world_tile(tile['heightmap'],tile['holes']))
            finally:
                for c,state in zip(components,states):c.set_collision_enabled(state)
            record['native_height_readback']=terrain
            if not terrain['passed']:raise RuntimeError('Native terrain differs from unchanged R16')
            yield
            for target,info in targets:
                data=json.loads(Path(info['source']).read_text());v=data['vertices_cm'];tri=data['triangles'];loc=info['location_cm']
                ignored=[a for a in actors.get_all_level_actors() if a!=target]
                eligible=[]
                for face in tri:
                    a,b,c=[v[i] for i in face]
                    if abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))>=25:eligible.append(face)
                if not eligible:raise RuntimeError('No substantial native shoulder faces to probe')
                for face in eligible[::max(1,len(eligible)//100)]:
                    center=[sum(v[i][axis] for i in face)/3+loc[axis] for axis in range(3)]
                    hit=unreal.SystemLibrary.line_trace_single(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),
                        unreal.Vector(center[0],center[1],center[2]+20),unreal.Vector(center[0],center[1],center[2]-20),
                        unreal.TraceTypeQuery.ECC_VISIBILITY,False,ignored,unreal.DrawDebugTrace.NONE,True)
                    if isinstance(hit,tuple):hit=next((h for h in hit if isinstance(h,unreal.HitResult)),None)
                    fields=hit.to_dict() if hit else {}
                    passed=bool(fields.get('blocking_hit') and fields.get('hit_actor')==target)
                    record['collision_probes'].append({'mesh':info['id'],'passed':passed})
                    if not passed:raise RuntimeError('Native shoulder collision probe missed '+info['id'])
            levels.save_current_level();record['saved_complete']=True;save()
            unreal.log('NATIVE_SHOULDER_IMPORTED '+tile['id'])
        if not all(sha(p)==value for p,value in before.items()):raise RuntimeError('Protected parent or active file changed')
        journal.update(all_imported=len(journal['tiles'])==len(changed),protected_files_unchanged=True,ended_unix=time.time());save()
        report={'build_id':build,'manifest':str(manifest),'all_imported':journal['all_imported'],
            'parent_import':str(Path(repair['parent_draft'])/'import_report.json'),'journal':str(journal_path),
            'map':'/Game/Maps/CircuitoGuidabile','activated':False,'root_map_modified':False,
            'terrain_asphalt_and_structures_preserved':True,'native_shoulder_probes':sum(len(t['collision_probes']) for t in journal['tiles'].values()),
            'visual_review_complete':False}
        (draft/'import_report.json').write_text(json.dumps(report,indent=2))
        unreal.log('NATIVE_SHOULDER_REPAIR_IMPORTED '+build)
    except BaseException as error:
        journal.update(error=repr(error),ended_unix=time.time());save();raise


iterator=work();last_step=time.monotonic();advancing=False
unreal.EditorPythonScripting.set_keep_python_script_alive(True)


def tick(_):
    global last_step,advancing
    # Native mesh compilation can pump Slate events synchronously. Never resume
    # the same generator from a nested editor callback.
    if advancing or time.monotonic()-last_step<1:return
    last_step=time.monotonic()
    advancing=True
    try:next(iterator)
    except StopIteration:
        unreal.unregister_slate_post_tick_callback(handle);unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    except BaseException:
        import traceback
        unreal.log_error(traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(handle);unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    finally:advancing=False


handle=unreal.register_slate_post_tick_callback(tick)
