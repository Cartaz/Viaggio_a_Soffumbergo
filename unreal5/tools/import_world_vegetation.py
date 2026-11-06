"""Native PCG on isolated full-world levels; persist complete regeneration evidence."""
import array
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import time
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve().parent
manifest_path = Path(os.environ['SOFFUMBERGO_WORLD_PCG_MANIFEST'])
m = json.loads(manifest_path.read_text()); v = m['vegetation']; build = m['build_id']
masks = json.loads(Path(v['mask_manifest']).read_text()); cfg = v['config']; draft = ROOT/'results/road_drafts'/build
old = json.loads(Path(v['parent_manifest']).read_text())
assets = unreal.EditorAssetLibrary; levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); tools = unreal.AssetToolsHelpers.get_asset_tools()
sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
asset_file = lambda p, s: ROOT/'Unreal/Content'/(p.removeprefix('/Game/')+s)
protected = [ROOT/'parameters/current_road_design.json', ROOT/'Unreal/Content/Data/circuit_driving_world.json',
    ROOT/'Unreal/Content/Data/circuit_itinerary.json', ROOT/'Unreal/Content/Maps/CircuitoGuidabile.umap', ROOT/'Unreal/Content/Maps/ValleLiDAR.umap']
protected += [asset_file(t['map'], '.umap') for t in old['tiles']]+[asset_file(r['asset'], '.uasset') for r in old['meshes']]
protected += list((ROOT/'Unreal/Content/Vegetation').glob('*.uasset'))
asset_probe = json.loads(Path(v['asset_probe']).read_text())
protected += [Path(r['asset_file']) for r in asset_probe['meshes']]
if not all(sha(r['asset_file']) == r['asset_sha256'] for r in asset_probe['meshes']): raise RuntimeError('Proven trunk assets changed')
before = {str(f): sha(f) for f in protected}
if not all(sha(f) == h for f, h in v['input_sha256'].items()): raise RuntimeError('World PCG inputs changed')
attempt = os.environ.get('SOFFUMBERGO_WORLD_PCG_ATTEMPT', 'v1')
if not attempt.replace('_', '').isalnum(): raise ValueError('Unsafe import attempt')
journal_path = draft/('world_pcg_native_'+attempt+'.json')
if journal_path.exists(): raise RuntimeError('Preserve previous import evidence')
resume_path = os.environ.get('SOFFUMBERGO_WORLD_PCG_RESUME'); prior = {}
if resume_path:
    resume = json.loads(Path(resume_path).read_text())
    if resume['build_id'] != build or resume['protected_before'] != before: raise RuntimeError('Resume state differs')
    prior = {k: r for k, r in resume['tiles'].items() if r.get('saved_complete')}
journal = {'build_id': build, 'started_unix': time.time(), 'protected_before': before, 'tiles': dict(prior),
           'all_imported': False, 'resume_journal': resume_path, 'diagnostic_tile_limit': int(os.environ.get('SOFFUMBERGO_WORLD_PCG_TILE_LIMIT', '0'))}
ready = False; mesh_info = {}; loaded_meshes = {}


def save(): journal_path.write_text(json.dumps(journal, indent=2))


def generated(_):
    global ready
    ready = True


def make_graph(tile, row):
    base = '/Game/World/Driving/P_'+build
    graph = tools.create_asset('PCG_'+tile['id'], base+'/Graphs', unreal.PCGGraph, unreal.PCGGraphFactory())
    source, _ = graph.add_node_of_type(unreal.PCGGetLandscapeSettings)
    if sha(tile['heightmap']) != tile['height_sha256']: raise RuntimeError('Native ground bytes changed')
    factory = unreal.DataAssetFactory(); factory.set_editor_property('data_asset_class', unreal.LidarNativeGroundGrid)
    ground = tools.create_asset('Ground_'+tile['id'], base+'/Ground', unreal.LidarNativeGroundGrid, factory)
    source_info = json.loads((ROOT/'terrain/world_tiles/manifest.json').read_text())
    ground.set_editor_property('samples', tile['samples']); ground.set_editor_property('spacing_cm', tile['xy_scale_cm'])
    ground.set_editor_property('origin_cm', unreal.Vector(*tile['bounds_xy_cm'][:2], (source_info['source_height_bounds_m'][0]-m['origin_ENH_m'][2])*100))
    ground.set_editor_property('quantum_cm', source_info['height_quantization_m']*100)
    ground.set_editor_property('heights', list(array.array('H', Path(tile['heightmap']).read_bytes())))
    ground.set_editor_property('provenance', json.dumps({'source_r16': tile['heightmap'], 'sha256': tile['height_sha256'], 'projection': 'Exact native diagonal triangles, unchanged R16 quantizer and LiDAR origin; no smoothing.'}))
    assets.save_loaded_asset(ground)
    for branch in cfg['branches']:
        data = row['branches'][branch['id']]
        if not data['allowed_cells']: continue
        if sha(data['mask_file']) != data['mask_sha256']: raise RuntimeError('Mask bytes changed')
        factory = unreal.DataAssetFactory(); factory.set_editor_property('data_asset_class', unreal.LidarVegetationMask)
        mask = tools.create_asset('Mask_'+tile['id']+'_'+branch['id'], base+'/Masks', unreal.LidarVegetationMask, factory)
        for key in ['width', 'height', 'spacing_cm']: mask.set_editor_property(key, row[key])
        mask.set_editor_property('origin_cm', unreal.Vector(*row['origin_cm']))
        mask.set_editor_property('cells', list(Path(data['mask_file']).read_bytes()))
        mask.set_editor_property('provenance', json.dumps({'mask_build_id': masks['mask_build_id'], 'tile': tile['id'], 'branch': branch['id'], 'mask_sha256': data['mask_sha256'], 'dimensions_status': cfg['dimensions_status']}))
        assets.save_loaded_asset(mask)
        sample, settings = graph.add_node_of_type(unreal.PCGSurfaceSamplerSettings)
        settings.set_editor_property('points_per_squared_meter', branch['density_m2'])
        e = branch['point_extent_cm']; settings.set_editor_property('point_extents', unreal.Vector(e, e, e)); settings.set_editor_property('seed', cfg['seed'])
        node, filt = graph.add_node_of_type(unreal.PCGLidarVegetationSettings)
        for key, value in [('mask', mask), ('native_ground', ground), ('required_class', 1), ('max_slope_degrees', branch['max_slope_degrees']), ('min_scale', branch['min_scale']), ('max_scale', branch['max_scale']), ('seed', cfg['seed'])]: filt.set_editor_property(key, value)
        spawn, sp = graph.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
        sp.set_mesh_selector_type(unreal.PCGMeshSelectorWeighted); sp.set_editor_property('synchronous_load', True); sp.set_editor_property('seed', cfg['seed'])
        selector = sp.get_editor_property('mesh_selector_parameters'); entries = []
        for name in branch['meshes']:
            entry = unreal.PCGMeshSelectorWeightedEntry(); descriptor = entry.get_editor_property('descriptor')
            descriptor.set_editor_property('static_mesh', loaded_meshes[name])
            descriptor.set_editor_property('instance_start_cull_distance', int(branch['cull_cm']*.8)); descriptor.set_editor_property('instance_end_cull_distance', branch['cull_cm'])
            descriptor.set_editor_property('cast_shadow', branch['id'] != 'grass')
            body = descriptor.get_editor_property('body_instance')
            body.set_editor_property('collision_profile_name', 'BlockAll' if branch['collision'] else 'NoCollision')
            body.set_editor_property('collision_enabled', unreal.CollisionEnabled.QUERY_AND_PHYSICS if branch['collision'] else unreal.CollisionEnabled.NO_COLLISION)
            descriptor.set_editor_property('body_instance', body)
            entry.set_editor_property('descriptor', descriptor); entry.set_editor_property('weight', 1); entries.append(entry)
        selector.set_editor_property('mesh_entries', entries)
        for a, ap, b, bp in [(source, 'Out', sample, 'Surface'), (sample, 'Out', node, 'In'), (node, 'Out', spawn, 'In'), (spawn, 'Out', graph.get_output_node(), 'Out')]: graph.add_edge(a, ap, b, bp)
    assets.save_loaded_asset(graph); return graph


def snapshot(area):
    rows = []; counts = {}; modes = {}
    for component in area.get_components_by_class(unreal.InstancedStaticMeshComponent):
        mesh = component.get_editor_property('static_mesh')
        if not mesh: continue
        name = mesh.get_name().removeprefix('SM_'); count = component.get_instance_count()
        counts[name] = counts.get(name, 0)+count; modes[name] = str(component.get_collision_enabled())
        for i in range(count):
            t = component.get_instance_transform(i, world_space=True); p = t.translation; q = t.rotation; s = t.scale3d
            rows.append([name, *[round(a, 4) for a in [p.x, p.y, p.z, q.x, q.y, q.z, q.w, s.x, s.y, s.z]]])
    rows.sort(); payload = json.dumps(rows, separators=(',', ':')).encode()
    return {'counts': counts, 'instances': len(rows), 'sha256': hashlib.sha256(payload).hexdigest(), 'collision_modes': modes}, rows


def validate_points(rows, tile, mask_row):
    n = tile['samples']; values = array.array('H', Path(tile['heightmap']).read_bytes())
    data = {k: Path(b['mask_file']).read_bytes() for k, b in mask_row['branches'].items()}
    branch_by_mesh = {name: b for b in cfg['branches'] for name in b['meshes']}
    base = json.loads((ROOT/'terrain/world_tiles/manifest.json').read_text())
    quant = base['height_quantization_m']; zero = base['source_height_bounds_m'][0]-m['origin_ENH_m'][2]
    x0, y0 = tile['bounds_xy_cm'][:2]; errors = []; violations = 0
    for r in rows:
        branch = branch_by_mesh[r[0]]; u = (r[1]-x0)/tile['xy_scale_cm']; w = (r[2]-y0)/tile['xy_scale_cm']
        mx = math.floor(u+.5); my = math.floor(w+.5)
        if not (0 <= mx < n and 0 <= my < n) or data[branch['id']][my*n+mx] != 1: violations += 1
        ix = math.floor(u); iy = math.floor(w); fx = u-ix; fy = w-iy
        if not (0 <= ix < n-1 and 0 <= iy < n-1): raise RuntimeError('PCG plant outside native tile')
        a, b, c, d = [values[j*n+i] for i, j in [(ix, iy), (ix+1, iy), (ix, iy+1), (ix+1, iy+1)]]
        height = a+(b-a)*fx+(d-b)*fy if fx >= fy else a+(d-c)*fx+(c-a)*fy
        errors.append(abs(r[3]-(height*quant+zero)*100))
    result = {'mask_violations': violations, 'maximum_native_ground_error_cm': max(errors, default=0), 'instances_checked': len(rows)}
    if violations: raise RuntimeError('Native PCG instances violate mask')
    return result


def work():
    global ready
    try:
        by_id = {t['tile']: t for t in masks['tiles']}
        for branch in cfg['branches']:
            for name in branch['meshes']:
                path = '/Game/Vegetation/'+('WorldPCG_20261024_v1/' if branch['collision'] else '')+'SM_'+name
                mesh = unreal.load_asset(path)
                if mesh is None: raise RuntimeError('Missing native foliage mesh '+path)
                info = json.loads(unreal.LidarTerrainLibrary.inspect_procedural_foliage(path)); loaded_meshes[name] = mesh
                radius = math.hypot(max(abs(info['min_cm'][0]), abs(info['max_cm'][0])), max(abs(info['min_cm'][1]), abs(info['max_cm'][1])))*branch['max_scale']/100
                if radius > branch['plant_radius_m']: raise RuntimeError('Plant exceeds mask clearance envelope '+name)
                if branch['collision'] and len(info['convex_hulls_cm']) != 1: raise RuntimeError('Tree lacks trunk hull')
                mesh_info[name] = {'asset': path, 'asset_sha256': sha(asset_file(path, '.uasset')), 'maximum_plan_envelope_radius_m': radius, 'native_info': info}
        journal['mesh_info'] = mesh_info; save(); completed_this_attempt = 0
        for tile in m['tiles']:
            if tile['id'] not in v['changed_tiles']: continue
            if tile['id'] in prior:
                if sha(asset_file(tile['map'], '.umap')) != prior[tile['id']]['saved_map_sha256']: raise RuntimeError('Completed map changed before resume')
                continue
            if assets.does_asset_exist(tile['map']): raise RuntimeError('Preserve untracked PCG level '+tile['map'])
            if not levels.new_level_from_template(tile['map'], tile['vegetation_parent_map']): raise RuntimeError('PCG map clone failed')
            parent_labels = {a.get_actor_label() for a in actors.get_all_level_actors()}
            row = by_id[tile['id']]; graph = make_graph(tile, row)
            x0, y0, x1, y1 = tile['bounds_xy_cm']
            area = actors.spawn_actor_from_class(unreal.LidarProceduralArea, unreal.Vector((x0+x1)/2, (y0+y1)/2, 0))
            label = 'Vegetazione_PCG_'+tile['id']; area.set_actor_label(label)
            bounds = area.get_component_by_class(unreal.BoxComponent); bounds.set_box_extent(unreal.Vector((x1-x0)/2, (y1-y0)/2, 100000), False)
            component = area.get_component_by_class(unreal.PCGComponent); component.set_graph(graph)
            component.on_pcg_graph_generated_external.add_callable(generated)
            record = {'map': tile['map'], 'parent_map': tile['vegetation_parent_map'], 'runs': [], 'saved_complete': False}
            journal['tiles'][tile['id']] = record; save(); baseline = None
            for stage, seed in enumerate([cfg['seed'], cfg['seed'], cfg['seed']+1, cfg['seed']]):
                component.set_editor_property('seed', seed); ready = False; started = time.monotonic(); component.generate_local(True)
                while not ready:
                    if time.monotonic()-started > 180: raise TimeoutError('PCG generation timeout '+tile['id'])
                    yield
                data, rows = snapshot(area); record['runs'].append({'seed': seed, **data}); save()
                if stage == 0: baseline = data
                elif stage in [1, 3] and data['sha256'] != baseline['sha256']: raise RuntimeError('Same/restored seed changed vegetation '+tile['id'])
                elif stage == 2 and baseline['instances'] > 0 and data['sha256'] == baseline['sha256']: raise RuntimeError('Changing seed did not change vegetation '+tile['id'])
                unreal.log('WORLD_PCG_STAGE '+tile['id']+' '+str(stage)+' '+str(data['instances'])); yield
            component.on_pcg_graph_generated_external.remove_callable(generated)
            record['point_validation'] = validate_points(rows, tile, row); save()
            if record['point_validation']['maximum_native_ground_error_cm'] > 2:
                raise RuntimeError('PCG roots differ from the native triangle surface by more than 2cm')
            for name, mode in data['collision_modes'].items():
                branch = next(b for b in cfg['branches'] if name in b['meshes'])
                expected = 'QUERY_AND_PHYSICS' if branch['collision'] else 'NO_COLLISION'
                if expected not in mode: raise RuntimeError('Unexpected PCG collision mode '+name)
            rows_path = draft/('pcg_instances_'+tile['id']+'.json.gz')
            if rows_path.exists(): raise RuntimeError('Preserve native instance evidence')
            with gzip.open(rows_path, 'wt', encoding='utf-8') as stream: json.dump(rows, stream, separators=(',', ':'))
            record['instance_rows'] = str(rows_path); record['instance_rows_sha256'] = sha(rows_path)
            record['parent_actor_labels_preserved'] = parent_labels.issubset({a.get_actor_label() for a in actors.get_all_level_actors()})
            if not record['parent_actor_labels_preserved']: raise RuntimeError('Parent scene actor removed')
            levels.save_current_level(); yield
            levels.new_level('/Game/World/Driving/P_'+build+'/UnsavedReloadProbe_'+tile['id'])
            if not levels.load_level(tile['map']): raise RuntimeError('Saved PCG map reload failed')
            yield
            area = next(a for a in actors.get_all_level_actors() if a.get_actor_label() == label)
            reloaded, _ = snapshot(area); record['reload_snapshot'] = reloaded
            if reloaded['sha256'] != baseline['sha256']: raise RuntimeError('PCG instances were not retained by the saved level')
            components = [c for a in actors.get_all_level_actors() for c in a.get_components_by_class(unreal.StaticMeshComponent)]
            states = [c.get_collision_enabled() for c in components]
            try:
                for c in components: c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                readback = json.loads(unreal.LidarTerrainLibrary.verify_lidar_world_tile(tile['heightmap'], tile['holes']))
            finally:
                for c, mode in zip(components, states): c.set_collision_enabled(mode)
            record['native_terrain_readback'] = readback
            if not readback['passed']: raise RuntimeError('Native PCG changed the terrain')
            world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(); probes = []
            for c in area.get_components_by_class(unreal.InstancedStaticMeshComponent):
                mesh = c.get_editor_property('static_mesh')
                if not mesh or not c.get_instance_count(): continue
                name = mesh.get_name().removeprefix('SM_')
                if not next(b for b in cfg['branches'] if name in b['meshes'])['collision']: continue
                points = mesh_info[name]['native_info']['convex_hulls_cm'][0]
                center = [sum(p[k] for p in points[72:90:2])/9 for k in range(3)]
                transform = c.get_instance_transform(0, world_space=True)
                p = unreal.MathLibrary.transform_location(transform, unreal.Vector(*center))
                hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(p.x-100, p.y, p.z), unreal.Vector(p.x+100, p.y, p.z),
                    unreal.TraceTypeQuery.ECC_VISIBILITY, False, [a for a in actors.get_all_level_actors() if a != area], unreal.DrawDebugTrace.NONE, True)
                if isinstance(hit, tuple): hit = next((h for h in hit if isinstance(h, unreal.HitResult)), None)
                fields = hit.to_dict() if hit else {}; passed = bool(fields.get('blocking_hit') and fields.get('hit_actor') == area)
                probes.append({'mesh': name, 'passed': passed})
                if not passed: raise RuntimeError('Reloaded instanced tree has no native trunk collision')
            record['native_trunk_collision_probes'] = probes
            record.update(saved_complete=True, saved_map_sha256=sha(asset_file(tile['map'], '.umap'))); save()
            completed_this_attempt += 1; unreal.log('WORLD_PCG_TILE_COMPLETE '+tile['id']+' '+str(reloaded['counts']))
            unreal.SystemLibrary.collect_garbage(); yield
            limit = journal['diagnostic_tile_limit']
            if limit and completed_this_attempt >= limit: break
        journal['protected_files_unchanged'] = all(sha(f) == h for f, h in before.items())
        if not journal['protected_files_unchanged']: raise RuntimeError('Parent or original game assets changed')
        journal['all_imported'] = len(journal['tiles']) == len(v['changed_tiles']) and all(t['saved_complete'] for t in journal['tiles'].values())
        journal['ended_unix'] = time.time(); save()
        if journal['all_imported']:
            total = sum(t['reload_snapshot']['instances'] for t in journal['tiles'].values())
            if total == 0: raise RuntimeError('Whole-world PCG produced no vegetation')
            report = {'build_id': build, 'manifest': str(manifest_path), 'all_imported': True, 'journal': str(journal_path),
                'map': '/Game/Maps/CircuitoGuidabile', 'activated': False, 'root_map_modified': False,
                'source_tile_count': len(m['tiles']), 'native_pcg_tiles': len(journal['tiles']), 'native_instances': total,
                'visual_review_complete': False, 'whole_route_rendered_test_complete': False}
            (draft/'import_report.json').write_text(json.dumps(report, indent=2)); unreal.log('WORLD_PCG_IMPORTED '+build)
        else: unreal.log('WORLD_PCG_DIAGNOSTIC_COMPLETE '+str(len(journal['tiles'])))
    except BaseException as error:
        journal.update(error=repr(error), ended_unix=time.time(), protected_files_unchanged=all(sha(f) == h for f, h in before.items())); save(); raise


iterator = work(); advancing = False; last_step = time.monotonic()
unreal.EditorPythonScripting.set_keep_python_script_alive(True)


def tick(_):
    global advancing, last_step
    if advancing or time.monotonic()-last_step < .5: return
    advancing = True; last_step = time.monotonic()
    try: next(iterator)
    except StopIteration:
        unreal.unregister_slate_post_tick_callback(handle); unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    except BaseException:
        import traceback
        unreal.log_error(traceback.format_exc()); unreal.unregister_slate_post_tick_callback(handle); unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    finally: advancing = False


handle = unreal.register_slate_post_tick_callback(tick)
