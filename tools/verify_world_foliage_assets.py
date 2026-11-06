"""Execute the optional native trunk hull path without touching original foliage."""
import hashlib
import json
from pathlib import Path
import time
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve().parent
out = ROOT/'results/world_foliage_asset_probe_20261024_v1.json'
if out.exists(): raise RuntimeError('Preserve previous native foliage probe')
assets = unreal.EditorAssetLibrary; actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
protected = [ROOT/'Unreal/Content/Vegetation'/(name+'.uasset') for name in ['SM_Tree_A', 'SM_Tree_B', 'SM_Tree_C', 'SM_Shrub_A', 'SM_Shrub_B', 'SM_Grass', 'M_Bark', 'M_Leaf']]
protected += [ROOT/'Unreal/Content/Maps/ValleLiDAR.umap', ROOT/'Unreal/Content/Maps/CircuitoGuidabile.umap', ROOT/'parameters/current_road_design.json']
sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
before = {str(f): sha(f) for f in protected}
report = {'started_unix': time.time(), 'passed': False, 'protected_before': before, 'meshes': []}
try:
    levels.new_level('/Game/TemporaryWorldFoliageProbe_20261024')
    for j, (name, seed) in enumerate([('Tree_A', 103), ('Tree_B', 214), ('Tree_C', 325)]):
        path = '/Game/Vegetation/WorldPCG_20261024_v1/SM_'+name
        if assets.does_asset_exist(path): raise RuntimeError('Preserve untracked foliage asset '+path)
        mesh = unreal.LidarTerrainLibrary.create_procedural_foliage(path, seed, 0, True)
        if mesh is None: raise RuntimeError('Native tree creation failed')
        assets.save_loaded_asset(mesh)
        info = json.loads(unreal.LidarTerrainLibrary.inspect_procedural_foliage(path))
        if not info['loaded'] or info['source_lods'] != 3 or len(info['convex_hulls_cm']) != 1:
            raise RuntimeError('Missing trunk-only hull or native LODs')
        points = info['convex_hulls_cm'][0]
        if len(points) != 144: raise RuntimeError('Unexpected native trunk ring count')
        center = [sum(p[k] for p in points[72:90:2])/9 for k in range(3)]
        location = [j*3000., 0., 0.]
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*location))
        component = actor.get_component_by_class(unreal.StaticMeshComponent); component.set_static_mesh(mesh)
        component.set_collision_profile_name('BlockAll'); component.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        probes = []
        for offset, expected in [(0., True), (150., False)]:
            p = [center[k]+location[k] for k in range(3)]; p[1] += offset
            hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(p[0]-100, p[1], p[2]),
                unreal.Vector(p[0]+100, p[1], p[2]), unreal.TraceTypeQuery.ECC_VISIBILITY, False,
                [a for a in actors.get_all_level_actors() if a != actor], unreal.DrawDebugTrace.NONE, True)
            if isinstance(hit, tuple): hit = next((h for h in hit if isinstance(h, unreal.HitResult)), None)
            fields = hit.to_dict() if hit else {}; blocked = bool(fields.get('blocking_hit') and fields.get('hit_actor') == actor)
            probes.append({'local_offset_cm': offset, 'expected_hit': expected, 'native_blocking_hit': blocked, 'passed': blocked == expected})
        if not all(p['passed'] for p in probes): raise RuntimeError('Native trunk/adjacent-space collision probe failed')
        f = ROOT/'Unreal/Content'/(path.removeprefix('/Game/')+'.uasset')
        report['meshes'].append({'name': name, 'seed': seed, 'asset': path, 'asset_file': str(f), 'asset_sha256': sha(f),
                                 'native_info': info, 'probes': probes})
    report['protected_files_unchanged'] = all(sha(f) == h for f, h in before.items())
    report['passed'] = report['protected_files_unchanged'] and len(report['meshes']) == 3
    report['source_sha256'] = {str(f): sha(f) for f in [ROOT/'Unreal/Source/SoffumbergoTerrainEditor/ProceduralFoliage.cpp', ROOT/'Unreal/Source/SoffumbergoTerrainEditor/LidarTerrainLibrary.h', Path(__file__)]}
    report['terrain_editor_dll_sha256'] = sha(ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoTerrainEditor.dll')
    report['scope'] = 'Three optional native trunk collision hulls and three LODs, positive/negative simple ray tests. No full-world PCG or physical vehicle contact claim.'
except BaseException as error:
    report['error'] = repr(error); raise
finally:
    report['ended_unix'] = time.time(); out.write_text(json.dumps(report, indent=2)); unreal.log('WORLD_FOLIAGE_ASSET_PROBE '+str(report['passed']))
