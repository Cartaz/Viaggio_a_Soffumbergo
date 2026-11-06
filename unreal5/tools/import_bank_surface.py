"""Native material authoring in an isolated cloned PCG Landscape level."""
import hashlib
import json
import os
from pathlib import Path
import time
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve().parent
manifest_path = Path(os.environ['SOFFUMBERGO_BANK_SURFACE_MANIFEST'])
m = json.loads(manifest_path.read_text()); v = m['bank_surface']; cfg = v['config']; build = m['build_id']
draft = ROOT/'results/road_drafts'/build
assets = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
lib = unreal.MaterialEditingLibrary
tile = next(t for t in m['tiles'] if t['id'] == cfg['tile'])
old = json.loads(Path(v['parent_manifest']).read_text())


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def asset_file(p, suffix): return ROOT/'Unreal/Content'/(p.removeprefix('/Game/')+suffix)


protected = [ROOT/'parameters/current_road_design.json', ROOT/'Unreal/Content/Data/circuit_driving_world.json',
    ROOT/'Unreal/Content/Data/circuit_itinerary.json', ROOT/'Unreal/Content/Maps/CircuitoGuidabile.umap',
    ROOT/'Unreal/Content/World/Materials/M_LidarWorld.uasset']
protected += [asset_file(t['map'], '.umap') for t in old['tiles']]
protected += [asset_file(r['asset'], '.uasset') for r in old['meshes']]
before = {str(p): sha(p) for p in protected}
journal_path = draft/'bank_surface_native_import.json'
if journal_path.exists(): raise RuntimeError('Preserve previous import journal')
journal = {'build_id': build, 'started_unix': time.time(), 'protected_before': before, 'all_imported': False}


def save(): journal_path.write_text(json.dumps(journal, indent=2))
save()


def snapshot():
    def transform(t):
        p, q, s = t.translation, t.rotation, t.scale3d
        return [p.x, p.y, p.z, q.x, q.y, q.z, q.w, s.x, s.y, s.z]
    rows = []; instances = []; modes = {}; labels = []
    for a in actors.get_all_level_actors():
        label = str(a.get_actor_label()); labels.append(label)
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            mesh = c.get_editor_property('static_mesh')
            rows.append([label, c.get_name(), transform(a.get_actor_transform()), transform(c.get_relative_transform()),
                mesh.get_path_name() if mesh else None, str(c.get_collision_enabled()),
                str(c.get_collision_profile_name()), c.is_simulating_physics()])
            if isinstance(c, unreal.InstancedStaticMeshComponent):
                modes[label+'/'+c.get_name()] = str(c.get_collision_enabled())
                for i in range(c.get_instance_count()):
                    t = c.get_instance_transform(i, world_space=True)
                    p, q, s = t.translation, t.rotation, t.scale3d
                    instances.append([label, mesh.get_path_name() if mesh else None,
                        *[round(x, 4) for x in [p.x, p.y, p.z, q.x, q.y, q.z, q.w, s.x, s.y, s.z]]])
    rows.sort(); instances.sort(); labels.sort()
    return {'actor_labels': labels, 'mesh_components': rows, 'instances': len(instances),
            'instance_sha256': hashlib.sha256(json.dumps(instances, separators=(',', ':')).encode()).hexdigest(),
            'instance_collision_modes': modes}


def work():
    try:
        assert json.loads((draft/'bank_surface_mask_audit.json').read_text())['passed']
        assert sha(v['mask_file']) == v['mask_sha256']
        for path in [tile['map'], v['material_asset'], v['texture_asset']]:
            if assets.does_asset_exist(path): raise RuntimeError('Preserve existing native asset '+path)
        if not levels.load_level(tile['surface_parent_map']): raise RuntimeError('Parent load failed')
        parent_state = snapshot(); journal['parent_state'] = parent_state; save()
        terrain = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.LandscapeProxy)]
        if len(terrain) != 1: raise RuntimeError('Expected one Landscape')
        source_material = terrain[0].get_editor_property('landscape_material')
        source_hole_material = terrain[0].get_editor_property('landscape_hole_material')
        journal['source_material'] = source_material.get_path_name()
        journal['source_hole_material'] = source_hole_material.get_path_name() if source_hole_material else None
        source_physical = source_material.get_editor_property('phys_material')
        tasks = unreal.AssetImportTask()
        tasks.set_editor_property('filename', v['mask_file'])
        tasks.set_editor_property('destination_path', v['texture_asset'].rsplit('/', 1)[0])
        tasks.set_editor_property('destination_name', v['texture_asset'].rsplit('/', 1)[1])
        tasks.set_editor_property('automated', True); tasks.set_editor_property('save', True)
        tasks.set_editor_property('replace_existing', False)
        tasks.set_editor_property('factory', unreal.TextureFactory())
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([tasks])
        tex = unreal.load_asset(v['texture_asset'])
        if not isinstance(tex, unreal.Texture2D): raise RuntimeError('Mask import failed')
        tex.set_editor_property('srgb', False)
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
        tex.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
        tex.set_editor_property('filter', unreal.TextureFilter.TF_BILINEAR)
        assets.save_loaded_asset(tex)
        mat = assets.duplicate_asset(source_material.get_path_name().split('.')[0], v['material_asset'])
        if not isinstance(mat, unreal.Material): raise RuntimeError('Expected a duplicated native material')
        original_base = lib.get_material_property_input_node(mat, unreal.MaterialProperty.MP_BASE_COLOR)
        original_output = lib.get_material_property_input_node_output_name(mat, unreal.MaterialProperty.MP_BASE_COLOR)
        if not original_base: raise RuntimeError('Preserve original base color input')
        preserved = {str(p): lib.get_material_property_input_node(mat, p) for p in [
            unreal.MaterialProperty.MP_NORMAL, unreal.MaterialProperty.MP_ROUGHNESS,
            unreal.MaterialProperty.MP_OPACITY_MASK, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET]}

        def node(cls): return lib.create_material_expression(mat, cls)
        def connect(a, output, b, pin):
            if not lib.connect_material_expressions(a, output, b, pin): raise RuntimeError('Material pin failed '+pin)
        def custom(code, output_type, names):
            c = node(unreal.MaterialExpressionCustom); c.set_editor_property('output_type', output_type)
            ins = []
            for name in names:
                i = unreal.CustomInput(); i.set_editor_property('input_name', name); ins.append(i)
            c.set_editor_property('inputs', ins); c.set_editor_property('code', code); return c

        p = node(unreal.MaterialExpressionWorldPosition)
        normal = node(unreal.MaterialExpressionVertexNormalWS)
        x0, y0 = tile['bounds_xy_cm'][:2]
        uv = custom(f'return ((P.xy-float2({x0:.9f},{y0:.9f}))/{tile["xy_scale_cm"]:.9f}+0.5)/{cfg["texture_size"]:.9f};',
            unreal.CustomMaterialOutputType.CMOT_FLOAT2, ['P'])
        connect(p, '', uv, 'P')
        sample = node(unreal.MaterialExpressionTextureSample)
        sample.set_editor_property('texture', tex)
        sample.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        connect(uv, '', sample, 'UVs')
        color = lambda key: 'float3('+','.join(f'{x:.9f}' for x in cfg[key])+')'
        code = '''struct BankNoise {
 float hash(float3 x) { x=frac(x*0.1031); x+=dot(x,x.yzx+33.33); return frac((x.x+x.y)*x.z); }
 float noise(float3 p) {
  float3 i=floor(p),f=frac(p); f=f*f*(3-2*f);
  return lerp(lerp(lerp(hash(i),hash(i+float3(1,0,0)),f.x),lerp(hash(i+float3(0,1,0)),hash(i+float3(1,1,0)),f.x),f.y),
   lerp(lerp(hash(i+float3(0,0,1)),hash(i+float3(1,0,1)),f.x),lerp(hash(i+float3(0,1,1)),hash(i+1),f.x),f.y),f.z);
 }
};
BankNoise b;
float3 p=P*0.01;
float broad=b.noise(p*0.48);
float grain=b.noise(p*19.0);
float detail=b.noise(p*4.1);
float strata=0.5+0.5*sin((p.z*3.0+0.19*p.x+0.11*p.y+detail*1.3)*6.2831853);
float crack=smoothstep(0.075,0.19,abs(b.noise(p*1.4+float3(13,29,7))-0.5));
float rockvalue=saturate(0.18+0.48*broad+0.18*detail+0.16*grain+0.07*strata);
float3 rock=lerp(ROCK_DARK,ROCK_LIGHT,rockvalue)*(0.64+0.36*crack);
float slope=saturate(1-abs(N.z));
float moss=smoothstep(0.39,0.69,b.noise(p*0.73+float3(41,2,17))+0.11*detail-0.08*slope);
float soil=smoothstep(0.62,0.83,b.noise(p*0.35+float3(4,19,11)))*(1-moss)*0.38;
float3 mosscolor=lerp(MOSS_DARK,MOSS_LIGHT,saturate(0.3+0.4*detail+0.3*grain));
return lerp(lerp(rock,SOIL,soil),mosscolor,moss*0.88);
'''
        for marker, key in [('ROCK_DARK','rock_dark_linear'), ('ROCK_LIGHT','rock_light_linear'),
            ('MOSS_DARK','moss_dark_linear'), ('MOSS_LIGHT','moss_light_linear'), ('SOIL','soil_linear')]:
            code = code.replace(marker, color(key))
        rock = custom(code, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ['P', 'N'])
        connect(p, '', rock, 'P'); connect(normal, '', rock, 'N')
        blend = node(unreal.MaterialExpressionLinearInterpolate)
        connect(original_base, original_output, blend, 'A'); connect(rock, '', blend, 'B')
        connect(sample, 'R', blend, 'Alpha')
        if not lib.connect_material_property(blend, '', unreal.MaterialProperty.MP_BASE_COLOR): raise RuntimeError('No base color')
        for prop in [unreal.MaterialProperty.MP_NORMAL, unreal.MaterialProperty.MP_ROUGHNESS,
            unreal.MaterialProperty.MP_OPACITY_MASK, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET]:
            if lib.get_material_property_input_node(mat, prop) != preserved[str(prop)]: raise RuntimeError('Unexpected noncolor material change')
        if mat.get_editor_property('phys_material') != source_physical: raise RuntimeError('Physical material changed')
        journal['physical_material_preserved'] = True
        journal['noncolor_outputs_preserved'] = True
        journal['hlsl_code_sha256'] = hashlib.sha256(code.encode()).hexdigest()
        lib.recompile_material(mat); assets.save_loaded_asset(mat); save(); yield
        if not levels.new_level_from_template(tile['map'], tile['surface_parent_map']): raise RuntimeError('Clone failed')
        journal['clone_state'] = snapshot(); save()
        if journal['clone_state'] != parent_state: raise RuntimeError('Cloning changed actors, instance transforms or collision')
        assigned = []
        for a in actors.get_all_level_actors():
            if isinstance(a, unreal.LandscapeProxy):
                a.set_editor_property('landscape_material', mat)
                if source_hole_material == source_material: a.set_editor_property('landscape_hole_material', mat)
                assigned.append(str(a.get_actor_label()))
        if len(assigned) != 1: raise RuntimeError('Wrong Landscape assignment count')
        if snapshot() != parent_state: raise RuntimeError('Material assignment changed geometry/PCG/collision')
        components = [c for a in actors.get_all_level_actors() for c in a.get_components_by_class(unreal.StaticMeshComponent)]
        states = [(c.get_collision_enabled(), c.get_collision_profile_name()) for c in components]
        try:
            for c in components: c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            terrain_check = json.loads(unreal.LidarTerrainLibrary.verify_lidar_world_tile(tile['heightmap'], tile['holes']))
        finally:
            for c, (enabled, profile) in zip(components, states):
                c.set_collision_enabled(enabled)
                c.set_collision_profile_name(profile)
        journal['native_terrain_readback'] = terrain_check
        if not terrain_check['passed']: raise RuntimeError('Height/visibility mismatch')
        if snapshot() != parent_state: raise RuntimeError('Readback failed to restore component physics')
        if not levels.save_current_level(): raise RuntimeError('Saving clone failed')
        save(); yield
        if not levels.new_level('/Temp/SurfaceReload_'+build): raise RuntimeError('Unload failed')
        if not levels.load_level(tile['map']): raise RuntimeError('Reload failed')
        reloaded = snapshot(); journal['reload_state'] = reloaded
        if reloaded != parent_state: raise RuntimeError('Reload changed geometry/PCG/collision')
        for a in actors.get_all_level_actors():
            if isinstance(a, unreal.LandscapeProxy) and a.get_editor_property('landscape_material') != mat: raise RuntimeError('Material not persisted')
        journal.update(assigned=assigned, geometry_and_pcg_preserved=True, saved_and_reloaded=True)
        journal['protected_files_unchanged'] = all(sha(p) == value for p, value in before.items())
        if not journal['protected_files_unchanged']: raise RuntimeError('Protected parent changed')
        journal.update(all_imported=True, ended_unix=time.time()); save()
        (draft/'import_report.json').write_text(json.dumps({'build_id': build, 'manifest': str(manifest_path),
            'all_imported': True, 'journal': str(journal_path), 'activated': False,
            'geometry_and_physics_changed': False, 'native_pcg_preserved': True,
            'actual_rendering_review_complete': False}, indent=2))
        unreal.log('BANK_SURFACE_IMPORTED '+build)
    except BaseException as e:
        journal.update(error=repr(e), ended_unix=time.time(),
            protected_files_unchanged=all(sha(p) == value for p, value in before.items()))
        save(); raise


generator = work(); advancing = False; last_step = time.monotonic()
unreal.EditorPythonScripting.set_keep_python_script_alive(True)


def tick(_):
    global advancing, last_step
    if advancing or time.monotonic()-last_step < 1: return
    advancing = True; last_step = time.monotonic()
    try: next(generator)
    except StopIteration:
        unreal.unregister_slate_post_tick_callback(handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    except BaseException:
        unreal.log_error(traceback.format_exc()); unreal.unregister_slate_post_tick_callback(handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    finally: advancing = False


handle = unreal.register_slate_post_tick_callback(tick)
