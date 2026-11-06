"""Clone one proven map, replace its native heightfield and two conformed overlays."""
import hashlib
import json
import os
from pathlib import Path
import time
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve().parent
manifest_path = Path(os.environ['SOFFUMBERGO_BANK_MANIFEST'])
m = json.loads(manifest_path.read_text()); change = m['bank_transition']; build = m['build_id']
draft = ROOT/'results/road_drafts'/build
audit = json.loads((draft/'structure_geometry_audit.json').read_text())
assert audit['passed'] and audit['build_id'] == build
old = json.loads(Path(change['parent_manifest']).read_text())
parent_import = json.loads((Path(change['parent_draft'])/'import_report.json').read_text())
assert parent_import['all_imported'] and parent_import['build_id'] == old['build_id']
assets = unreal.EditorAssetLibrary; levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def asset_file(path, suffix): return ROOT/'Unreal/Content'/(path.removeprefix('/Game/')+suffix)


protected = [ROOT/'parameters/current_road_design.json', ROOT/'Unreal/Content/Data/circuit_driving_world.json',
             ROOT/'Unreal/Content/Data/circuit_itinerary.json', ROOT/'Unreal/Content/Maps/CircuitoGuidabile.umap']
protected += [asset_file(t['map'], '.umap') for t in old['tiles']]
protected += [asset_file(r['asset'], '.uasset') for r in old['meshes']]
protected += [Path(t[k]) for t in old['tiles'] for k in ['heightmap', 'holes']]
before = {str(f): sha(f) for f in protected}
journal_path = draft/'bank_native_import_v1.json'
if journal_path.exists(): raise RuntimeError('Preserve previous native import')
journal = {'build_id': build, 'started_unix': time.time(), 'protected_before': before, 'all_imported': False}


def save(): journal_path.write_text(json.dumps(journal, indent=2))


def trace(world, point, target):
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(point[0], point[1], point[2]+30),
        unreal.Vector(point[0], point[1], point[2]-30), unreal.TraceTypeQuery.ECC_VISIBILITY, False,
        [a for a in actors.get_all_level_actors() if a != target], unreal.DrawDebugTrace.NONE, True)
    if isinstance(hit, tuple): hit = next((h for h in hit if isinstance(h, unreal.HitResult)), None)
    return hit.to_dict() if hit else {}


def work():
    try:
        tile = next(t for t in m['tiles'] if t['id'] == change['config']['tile'])
        if assets.does_asset_exist(tile['map']): raise RuntimeError('Preserving untracked level')
        if not levels.new_level_from_template(tile['map'], tile['bank_parent_map']): raise RuntimeError('Map clone failed')
        original_labels = {a.get_actor_label() for a in actors.get_all_level_actors()}
        terrain = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.Landscape)]
        if len(terrain) != 1: raise RuntimeError('Ambiguous parent Landscape')
        label = terrain[0].get_actor_label(); actors.destroy_actor(terrain[0])
        landscape = unreal.LidarTerrainLibrary.import_lidar_world_tile(tile['heightmap'], tile['holes'], unreal.Vector(*tile['location_cm']), tile['z_scale'])
        if landscape is None: raise RuntimeError('Native Landscape import failed')
        landscape.set_actor_label(label); landscape.set_editor_property('lod_group_key', 20261022)
        journal['map'] = tile['map']; journal['replaced_meshes'] = []; save(); yield
        targets = []
        for r in change['records']:
            if sha(r['source']) != r['sha256']: raise RuntimeError('Geometry bytes changed')
            previous = [a for a in actors.get_all_level_actors() if a.get_actor_label() == r['id']]
            if len(previous) != 1: raise RuntimeError('Ambiguous parent mesh actor '+r['id'])
            actor = previous[0]; component = actor.get_component_by_class(unreal.StaticMeshComponent)
            material = component.get_material(0)
            if material is None: raise RuntimeError('Missing parent material')
            # Retain the existing actor transform, tags, masked material and
            # collision mode. Only point it at a newly created isolated asset.
            mode = component.get_collision_enabled()
            mesh = unreal.LidarTerrainLibrary.create_circuit_mesh(r['source'], r['asset'], material.get_path_name())
            if mesh is None: raise RuntimeError('New native mesh failed')
            assets.save_loaded_asset(mesh); component.set_static_mesh(mesh); component.set_collision_enabled(mode)
            journal['replaced_meshes'].append({'id': r['id'], 'asset': mesh.get_path_name(), 'material': material.get_path_name(), 'collision_enabled': str(mode)})
            targets.append((actor, r)); save(); yield
        components = [a.get_component_by_class(unreal.StaticMeshComponent) for a in actors.get_all_level_actors() if isinstance(a, unreal.StaticMeshActor)]
        modes = [c.get_collision_enabled() for c in components]
        try:
            for c in components: c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            result = json.loads(unreal.LidarTerrainLibrary.verify_lidar_world_tile(tile['heightmap'], tile['holes']))
        finally:
            for c, mode in zip(components, modes): c.set_collision_enabled(mode)
        journal['native_height_readback'] = result; save()
        if not result['passed']: raise RuntimeError('Native Landscape verification failed')
        yield
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        probes = []
        for target, r in targets:
            data = json.loads(Path(r['source']).read_text()); vertices = data['vertices_cm']; tri = data['triangles']; location = r['location_cm']
            substantial = [f for f in tri if abs((vertices[f[1]][0]-vertices[f[0]][0])*(vertices[f[2]][1]-vertices[f[0]][1])-(vertices[f[1]][1]-vertices[f[0]][1])*(vertices[f[2]][0]-vertices[f[0]][0])) >= 25]
            if not substantial: raise RuntimeError('No substantial faces')
            for f in substantial[::max(1, len(substantial)//100)]:
                center = [sum(vertices[i][j] for i in f)/3+location[j] for j in range(3)]
                hit = trace(world, center, target)
                passed = bool(hit.get('blocking_hit') and hit.get('hit_actor') == target) if r['kind'] == 'shoulder' else not hit.get('blocking_hit')
                probes.append({'mesh': r['id'], 'passed': passed})
                if not passed: raise RuntimeError('Unexpected native overlay collision '+r['id'])
        journal['collision_probes'] = probes
        journal['actor_labels_preserved'] = original_labels == {a.get_actor_label() for a in actors.get_all_level_actors()}
        if not journal['actor_labels_preserved']: raise RuntimeError('Unexpected actor removal/addition')
        levels.save_current_level()
        journal['protected_files_unchanged'] = all(sha(f) == h for f, h in before.items())
        if not journal['protected_files_unchanged']: raise RuntimeError('Parent or active data changed')
        journal.update(all_imported=True, ended_unix=time.time()); save()
        report = {'build_id': build, 'manifest': str(manifest_path), 'all_imported': True,
                  'journal': str(journal_path), 'map': '/Game/Maps/CircuitoGuidabile', 'activated': False,
                  'root_map_modified': False, 'native_overlay_probes': len(probes), 'visual_review_complete': False}
        (draft/'import_report.json').write_text(json.dumps(report, indent=2))
        unreal.log('BANK_TRANSITION_IMPORTED '+build)
    except BaseException as error:
        journal.update(error=repr(error), ended_unix=time.time(), protected_files_unchanged=all(sha(f) == h for f, h in before.items()))
        save(); raise


iterator = work(); last_step = time.monotonic(); advancing = False
unreal.EditorPythonScripting.set_keep_python_script_alive(True)


def tick(_):
    global last_step, advancing
    if advancing or time.monotonic()-last_step < 1: return
    advancing = True; last_step = time.monotonic()
    try: next(iterator)
    except StopIteration:
        unreal.unregister_slate_post_tick_callback(handle); unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    except BaseException:
        import traceback
        unreal.log_error(traceback.format_exc()); unreal.unregister_slate_post_tick_callback(handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    finally: advancing = False


handle = unreal.register_slate_post_tick_callback(tick)
