"""Clone only affected parent levels, add roadside structures and query collision.

Run inside Unreal Editor. Parent map files and live runtime data are protected
by byte hashes. No original map is saved or replaced.
"""
import hashlib
import json
import os
from pathlib import Path
import time
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve().parent
manifest_path=Path(os.environ['SOFFUMBERGO_STRUCTURE_MANIFEST'])
m=json.loads(manifest_path.read_text());s=m['roadside_structures'];build=m['build_id']
draft=ROOT/'results/road_drafts'/build
geometry_audit=json.loads((draft/'structure_geometry_audit.json').read_text())
if geometry_audit.get('build_id')!=build or not geometry_audit.get('passed'):
    raise RuntimeError('A passing geometry audit for this exact candidate is required before native import')
parent=Path(s['parent_draft']);parent_import=json.loads((parent/'import_report.json').read_text())
if not parent_import['all_imported'] or parent_import['build_id']!=s['parent_build_id']:
    raise RuntimeError('Parent geometry has no accepted native import')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def map_file(name):return ROOT/'Unreal/Content'/(name.removeprefix('/Game/')+'.umap')


changed=[t for t in m['tiles'] if t.get('structure_parent_map')]
protected=[ROOT/'parameters/current_road_design.json',ROOT/'Unreal/Content/Data/circuit_driving_world.json',
           ROOT/'Unreal/Content/Data/circuit_itinerary.json',ROOT/'Unreal/Content/Maps/CircuitoGuidabile.umap']
protected += [map_file(t['structure_parent_map']) for t in changed]
before={str(p):sha(p) for p in protected}
resume_path=os.environ.get('SOFFUMBERGO_STRUCTURE_RESUME_JOURNAL')
tracked={}
if resume_path:
    resume=json.loads(Path(resume_path).read_text())
    if resume['build_id']!=build or resume['protected_before']!=before:
        raise RuntimeError('Resume journal does not match the unchanged parent')
    tracked=resume['tiles']
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assets=unreal.EditorAssetLibrary
attempt=os.environ.get('SOFFUMBERGO_STRUCTURE_ATTEMPT','v1')
if not attempt.replace('_','').isalnum():raise ValueError('Invalid attempt name')
journal_path=draft/('structure_native_import_'+attempt+'.json')
if journal_path.exists():raise RuntimeError('Preserve earlier import evidence; inspect its state before resuming')
journal={'build_id':build,'parent_build_id':s['parent_build_id'],'started_unix':time.time(),
         'protected_before':before,'tiles':{},'all_imported':False,'resume_journal':resume_path}
journal_path.write_text(json.dumps(journal,indent=2))
unreal.log('STRUCTURE_TRACE_API '+str(unreal.SystemLibrary.line_trace_single.__doc__))
unreal.log('STRUCTURE_HIT_API '+str(unreal.HitResult.__doc__))

def import_tiles():
    try:
        for tile in changed:
            if assets.does_asset_exist(tile['map']):
                previous=tracked.get(tile['id'])
                if not previous or previous['map']!=tile['map'] or previous['parent_map']!=tile['structure_parent_map']:
                    raise RuntimeError('Preserving untracked existing map '+tile['map'])
                levels.load_level(tile['map'])
                for actor in actors.get_all_level_actors():
                    if actor.actor_has_tag('RoadsideStructure'):actors.destroy_actor(actor)
            else:
                if not levels.new_level_from_template(tile['map'],tile['structure_parent_map']):
                    raise RuntimeError('Failed to clone parent tile '+tile['id'])
                replaced=set(s.get('replaced_mesh_ids',[]))
                expected={r['id'] for r in m['meshes'] if r['tile']==tile['id'] and r['id'] in replaced}
                removed=set()
                for actor in actors.get_all_level_actors():
                    if actor.actor_has_tag('RoadsideStructure') and actor.get_actor_label() in replaced:
                        removed.add(actor.get_actor_label());actors.destroy_actor(actor)
                if removed!=expected:raise RuntimeError('Parent structure replacement scope mismatch: '+str(removed^expected))
            record={'parent_map':tile['structure_parent_map'],'map':tile['map'],'meshes':[],
                    'collision_probes':[],'open_collision_probes':[],'saved_complete':False}
            journal['tiles'][tile['id']]=record
            targets={}
            for mesh_info in [r for r in s['records'] if r['tile']==tile['id']]:
                if sha(mesh_info['source'])!=mesh_info['sha256']:raise RuntimeError('Structure source changed')
                material='/Game/World/Materials/M_Road_'+mesh_info['kind']
                mesh=unreal.LidarTerrainLibrary.create_circuit_mesh(mesh_info['source'],mesh_info['asset'],material)
                if mesh is None:raise RuntimeError('Native mesh creation failed '+mesh_info['id'])
                assets.save_loaded_asset(mesh)
                actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*mesh_info['location_cm']))
                component=actor.get_component_by_class(unreal.StaticMeshComponent)
                component.set_static_mesh(mesh);component.set_collision_profile_name('BlockAll')
                component.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
                actor.set_actor_label(mesh_info['id']);actor.set_editor_property('tags',['RoadsideStructure'])
                targets[mesh_info['id']]=actor;record['meshes'].append(mesh_info['id'])
            journal_path.write_text(json.dumps(journal,indent=2))
            yield # Allow new mesh bodies and compilation to finish in editor ticks.
            # The parent tile already contains asphalt. Isolate the Landscape for
            # its height/collision readback, then restore every mesh's exact state
            # before structural probes, saving, or subsequent driving checks.
            components=[a.get_component_by_class(unreal.StaticMeshComponent) for a in actors.get_all_level_actors()
                        if isinstance(a,unreal.StaticMeshActor)]
            states=[c.get_collision_enabled() for c in components]
            try:
                for component in components:component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                terrain=json.loads(unreal.LidarTerrainLibrary.verify_lidar_world_tile(tile['heightmap'],tile['holes']))
            finally:
                for component,state in zip(components,states):component.set_collision_enabled(state)
            record['terrain_probe_scope']='Landscape isolated from mesh occlusion; all collision states restored before structural traces and save'
            record['native_height_readback']=terrain
            if not terrain['passed']:raise RuntimeError('Cloned Landscape differs from parent raster')
            yield # Allow restored physics states to enter the scene before querying.
            world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            all_actors=list(actors.get_all_level_actors())
            for probe in [p for p in s['collision_probes'] if p['mesh_id'] in targets]:
                target=targets[probe['mesh_id']]
                # Ignore the other actors to prove this exact imported structural
                # collision solid, rather than accepting a hit on the earthen bank.
                ignored=[a for a in all_actors if a!=target]
                hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(*probe['start_cm']),
                    unreal.Vector(*probe['end_cm']),unreal.TraceTypeQuery.ECC_VISIBILITY,False,ignored,
                    unreal.DrawDebugTrace.NONE,True)
                if isinstance(hit,tuple):hit=next((v for v in hit if isinstance(v,unreal.HitResult)),None)
                result=hit.to_dict() if hit is not None else None
                passed=result is not None and result.get('blocking_hit') and result.get('hit_actor')==target
                entry={'mesh_id':probe['mesh_id'],'passed':bool(passed)}
                if not passed:
                    entry.update({'hit':str(result),'target_location':str(target.get_actor_location()),
                                  'start_cm':probe['start_cm'],'end_cm':probe['end_cm'],
                                  'collision_state':str(target.get_component_by_class(unreal.StaticMeshComponent).get_collision_enabled())})
                    c=target.get_component_by_class(unreal.StaticMeshComponent)
                    entry['target_scale']=str(target.get_actor_scale3d())
                    entry['body_collision_mode']=str(c.static_mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag'))
                    entry['component_trace_api']=str(c.line_trace_component.__doc__)
                    diagnostic=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(*probe['start_cm']),
                        unreal.Vector(*probe['end_cm']),unreal.TraceTypeQuery.ECC_VISIBILITY,False,[],
                        unreal.DrawDebugTrace.NONE,True)
                    entry['unfiltered_world_hit']=str(diagnostic.to_dict()) if diagnostic is not None else None
                record['collision_probes'].append(entry)
                if not passed:raise RuntimeError('No collision hit on imported structure '+probe['mesh_id'])
            for probe in [p for p in s.get('open_collision_probes',[]) if p['tile']==tile['id']]:
                target=targets[probe['mesh_id']];ignored=[a for a in all_actors if a!=target]
                hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(*probe['start_cm']),
                    unreal.Vector(*probe['end_cm']),unreal.TraceTypeQuery.ECC_VISIBILITY,False,ignored,
                    unreal.DrawDebugTrace.NONE,True)
                if isinstance(hit,tuple):hit=next((v for v in hit if isinstance(v,unreal.HitResult)),None)
                result=hit.to_dict() if hit is not None else None
                passed=not result or not result.get('blocking_hit')
                record['open_collision_probes'].append({'control':probe['control'],'mesh_id':probe['mesh_id'],'passed':bool(passed)})
                if not passed:raise RuntimeError('Unexpected guardrail collision in observed open approach')
            levels.save_current_level();record['saved_complete']=True
            journal_path.write_text(json.dumps(journal,indent=2))
            unreal.log('ROADSIDE_TILE_IMPORTED '+tile['id'])
        if not all(sha(p)==value for p,value in before.items()):raise RuntimeError('Protected source changed')
        journal['all_imported']=all(r['saved_complete'] for r in journal['tiles'].values()) and len(journal['tiles'])==len(changed)
        journal['protected_files_unchanged']=True;journal['ended_unix']=time.time()
        journal_path.write_text(json.dumps(journal,indent=2))
        report={'build_id':build,'manifest':str(manifest_path),'all_imported':journal['all_imported'],'parent_import':str(parent/'import_report.json'),
            'structure_import':str(journal_path),'map':'/Game/Maps/CircuitoGuidabile','activated':False,
            'root_map_modified':False,'parent_height_and_pavement_data_preserved':True,
            'structure_collision_probes':sum(len(r['collision_probes']) for r in journal['tiles'].values()),
            'observed_open_collision_probes':sum(len(r['open_collision_probes']) for r in journal['tiles'].values()),
            'visual_review_complete':False}
        (draft/'import_report.json').write_text(json.dumps(report,indent=2))
        unreal.log('ROADSIDE_STRUCTURE_IMPORTED '+build+' '+json.dumps(report))
    except BaseException as error:
        journal['error']=repr(error);journal['ended_unix']=time.time()
        journal['protected_files_unchanged']=all(sha(p)==value for p,value in before.items())
        journal_path.write_text(json.dumps(journal,indent=2));raise


work=import_tiles()
last_step=time.monotonic()
advancing=False
unreal.EditorPythonScripting.set_keep_python_script_alive(True)

def tick(_):
    global last_step,advancing
    if advancing:return
    if time.monotonic()-last_step<1:return
    last_step=time.monotonic()
    advancing=True
    try:
        next(work)
    except StopIteration:
        unreal.unregister_slate_post_tick_callback(handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    except BaseException as error:
        import traceback
        unreal.log_error(traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    finally:
        advancing=False

handle=unreal.register_slate_post_tick_callback(tick)
