"""Import collision-free native far meshes/levels; prove saved data after reload."""
import hashlib
import json
import os
from pathlib import Path
import struct
import time
import traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve().parent
manifest_path=Path(os.environ['SOFFUMBERGO_DISTANT_MANIFEST']);m=json.loads(manifest_path.read_text());v=m['distant_terrain'];build=m['build_id']
draft=ROOT/'results/road_drafts'/build;assets=unreal.EditorAssetLibrary
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
lib=unreal.MaterialEditingLibrary


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def asset_file(p,suffix): return ROOT/'Unreal/Content'/(p.removeprefix('/Game/')+suffix)


old=json.loads(Path(v['parent_manifest']).read_text())
protected=[ROOT/'parameters/current_road_design.json',ROOT/'Unreal/Content/Data/circuit_driving_world.json',
    ROOT/'Unreal/Content/Data/circuit_itinerary.json',ROOT/'Unreal/Content/Maps/CircuitoGuidabile.umap',
    ROOT/'Unreal/Content/World/Materials/M_LidarWorld.uasset',ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoLab.dll',
    ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoTerrainEditor.dll']
protected += [asset_file(t['map'],'.umap') for t in old['tiles']]
protected += [asset_file(r['asset'],'.uasset') for r in old['meshes']]
protected += [Path(t[k]) for t in old['tiles'] for k in ['heightmap','holes']]
before={str(p):sha(p) for p in protected}
journal_path=draft/'distant_native_import.json'
if journal_path.exists(): raise RuntimeError('Preserve previous import')
journal={'build_id':build,'started_unix':time.time(),'protected_before':before,'tiles':{},'all_imported':False}


def save(): journal_path.write_text(json.dumps(journal,indent=2))
save()


def component_state(a,c):
    p=a.get_actor_location()
    return {'label':a.get_actor_label(),'location_cm':[p.x,p.y,p.z],
        'mesh':c.get_editor_property('static_mesh').get_path_name(),
        'collision':str(c.get_collision_enabled()),'profile':str(c.get_collision_profile_name()),
        'cast_shadow':c.get_editor_property('cast_shadow'),'simulating':c.is_simulating_physics(),
        'actor_hidden':bool(a.get_editor_property('hidden'))}


def work():
 try:
    assert json.loads(Path(v['geometry_audit']).read_text())['passed']
    for path,expected in v['input_sha256'].items():
        if sha(path)!=expected: raise RuntimeError('Import source changed '+path)
    for row in v['records']:
        if assets.does_asset_exist(row['asset']) or assets.does_asset_exist(row['map']): raise RuntimeError('Preserve existing untracked far asset')
    path=v['material_asset']
    if assets.does_asset_exist(path): raise RuntimeError('Preserve existing material')
    folder,name=path.rsplit('/',1)
    mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
    color=lib.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector)
    color.set_editor_property('constant',unreal.LinearColor(.12,.19,.055,1))
    rough=lib.create_material_expression(mat,unreal.MaterialExpressionConstant);rough.set_editor_property('r',.94)
    assert lib.connect_material_property(color,'',unreal.MaterialProperty.MP_BASE_COLOR)
    assert lib.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(mat);assets.save_loaded_asset(mat)
    for row in v['records']:
        assert sha(row['binary'])==row['binary_sha256']
        if not levels.new_level(row['map']): raise RuntimeError('Cannot create native far level')
        mesh=unreal.LidarTerrainLibrary.create_distant_terrain_mesh(row['binary'],row['asset'],path)
        if mesh is None: raise RuntimeError('Native far mesh creation failed '+row['id'])
        assets.save_loaded_asset(mesh)
        native=json.loads(unreal.LidarTerrainLibrary.verify_distant_terrain_mesh(row['binary'],row['asset']))
        if not native['passed']: raise RuntimeError('Native geometry/physics readback failed '+str(native))
        actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*row['location_cm']))
        actor.set_actor_label('Distant_'+row['id']);actor.set_editor_property('tags',['DistantTerrain'])
        c=actor.get_component_by_class(unreal.StaticMeshComponent);c.set_static_mesh(mesh)
        c.set_collision_profile_name('NoCollision');c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        c.set_editor_property('cast_shadow',False)
        c.set_editor_property('can_ever_affect_navigation',False)
        c.set_editor_property('affect_distance_field_lighting',False)
        c.set_editor_property('affect_dynamic_indirect_lighting',False)
        expected=component_state(actor,c)
        if c.get_collision_enabled()!=unreal.CollisionEnabled.NO_COLLISION or expected['cast_shadow'] or expected['simulating']: raise RuntimeError('Unsafe far component')
        if not levels.save_current_level(): raise RuntimeError('Far level save failed')
        journal['tiles'][row['id']]={'map':row['map'],'asset':row['asset'],'native_geometry':native,
            'component':expected,'saved_and_reloaded':False};save();yield
        if not levels.new_level('/Temp/FarReload_'+build+'_'+row['id']): raise RuntimeError('Unload failed')
        if not levels.load_level(row['map']): raise RuntimeError('Reload failed')
        targets=[a for a in actors.get_all_level_actors() if a.actor_has_tag('DistantTerrain')]
        if len(targets)!=1: raise RuntimeError('Unexpected far actor count')
        a=targets[0];c=a.get_component_by_class(unreal.StaticMeshComponent)
        if component_state(a,c)!=expected: raise RuntimeError('Far component changed after reload')
        result=json.loads(unreal.LidarTerrainLibrary.verify_distant_terrain_mesh(row['binary'],row['asset']))
        if not result['passed']: raise RuntimeError('Native geometry changed after reload')
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        data=Path(row['binary']).read_bytes();nv,nt=struct.unpack_from('<II',data,8)
        probes=[]
        for index in sorted(set([0,nt//2,nt-1])):
            ids=struct.unpack_from('<III',data,16+nv*24+index*12)
            xyz=[struct.unpack_from('<ddd',data,16+i*24) for i in ids]
            center=[sum(p[k] for p in xyz)/3+row['location_cm'][k] for k in range(3)]
            hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(center[0],center[1],center[2]+1000),
                unreal.Vector(center[0],center[1],center[2]-1000),unreal.TraceTypeQuery.ECC_VISIBILITY,False,
                [other for other in actors.get_all_level_actors() if other!=a],unreal.DrawDebugTrace.NONE,True)
            if isinstance(hit,tuple): hit=next((q for q in hit if isinstance(q,unreal.HitResult)),None)
            blocking=bool(hit and hit.to_dict().get('blocking_hit'))
            probes.append({'triangle':index,'no_collision':not blocking})
            if blocking: raise RuntimeError('Far terrain introduced collision')
        journal['tiles'][row['id']].update(saved_and_reloaded=True,native_reload_geometry=result,no_collision_probes=probes)
        save();unreal.log('DISTANT_TILE_IMPORTED '+row['id']);yield
    journal['protected_files_unchanged']=all(sha(p)==expected for p,expected in before.items())
    if not journal['protected_files_unchanged']: raise RuntimeError('Protected parent changed')
    journal.update(all_imported=len(journal['tiles'])==113 and all(r['saved_and_reloaded'] for r in journal['tiles'].values()),ended_unix=time.time());save()
    (draft/'import_report.json').write_text(json.dumps({'build_id':build,'manifest':str(manifest_path),'all_imported':journal['all_imported'],
        'journal':str(journal_path),'activated':False,'near_geometry_physics_and_pcg_changed':False,'distant_tiles':len(journal['tiles']),
        'native_no_collision_probes':sum(len(r['no_collision_probes']) for r in journal['tiles'].values()),
        'runtime_streaming_verified':False,'visual_quality_approved':False},indent=2))
    unreal.log('DISTANT_WORLD_IMPORTED '+build)
 except BaseException as e:
    journal.update(error=repr(e),ended_unix=time.time(),protected_files_unchanged=all(sha(p)==expected for p,expected in before.items()));save();raise


generator=work();last_step=time.monotonic();advancing=False
unreal.EditorPythonScripting.set_keep_python_script_alive(True)


def tick(_):
    global advancing,last_step
    if advancing or time.monotonic()-last_step<.2:return
    advancing=True;last_step=time.monotonic()
    try:next(generator)
    except StopIteration:
        unreal.unregister_slate_post_tick_callback(handle);unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    except BaseException:
        unreal.log_error(traceback.format_exc());unreal.unregister_slate_post_tick_callback(handle);unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    finally:advancing=False


handle=unreal.register_slate_post_tick_callback(tick)
