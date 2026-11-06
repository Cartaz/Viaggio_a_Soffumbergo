"""Import a local shoulder finish in a cloned PCG level, without a renderer."""
import hashlib
import json
import os
from pathlib import Path
import time
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve().parent
manifest_path = Path(os.environ['SOFFUMBERGO_DRAINAGE_MANIFEST'])
m = json.loads(manifest_path.read_text()); v = m['drainage_surface']; cfg = v['config']; build = m['build_id']
draft = ROOT/'results/road_drafts'/build
assets = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
lib = unreal.MaterialEditingLibrary
tile = next(t for t in m['tiles'] if t['id'] == cfg['tile'])
parent = json.loads(Path(v['parent_manifest']).read_text())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def asset_file(path, suffix):
    return ROOT/'Unreal/Content'/(path.removeprefix('/Game/')+suffix)


protected = [ROOT/'parameters/current_road_design.json', ROOT/'Unreal/Content/Data/circuit_driving_world.json',
    ROOT/'Unreal/Content/Data/circuit_itinerary.json', ROOT/'Unreal/Content/Maps/CircuitoGuidabile.umap',
    ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoLab.dll',
    ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoTerrainEditor.dll']
protected += [asset_file(t['map'], '.umap') for t in parent['tiles']]
protected += [asset_file(r['asset'], '.uasset') for r in parent['meshes']]
protected += [Path(t[key]) for t in parent['tiles'] for key in ['heightmap', 'holes']]
protected += [asset_file(r[key], suffix) for r in parent['distant_terrain']['records']
              for key, suffix in [('asset', '.uasset'), ('map', '.umap')]]
before = {str(p): sha(p) for p in protected}
journal_path = draft/'drainage_native_import.json'
if journal_path.exists(): raise RuntimeError('Preserve the earlier drainage import')
journal = {'build_id': build, 'started_unix': time.time(), 'protected_before': before,
    'import_script_sha256': sha(__file__), 'all_imported': False, 'rendering_executed': False}


def save():
    journal_path.write_text(json.dumps(journal, indent=2))


def transform(t):
    p, q, s = t.translation, t.rotation, t.scale3d
    return [p.x, p.y, p.z, q.x, q.y, q.z, q.w, s.x, s.y, s.z]


def snapshot():
    rows = []; instances = []; labels = []; modes = {}
    for actor in actors.get_all_level_actors():
        label = str(actor.get_actor_label()); labels.append(label)
        for c in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = c.get_editor_property('static_mesh')
            rows.append([label, c.get_name(), transform(actor.get_actor_transform()), transform(c.get_relative_transform()),
                mesh.get_path_name() if mesh else None, str(c.get_collision_enabled()),
                str(c.get_collision_profile_name()), c.is_simulating_physics()])
            if isinstance(c, unreal.InstancedStaticMeshComponent):
                modes[label+'/'+c.get_name()] = str(c.get_collision_enabled())
                for i in range(c.get_instance_count()):
                    instances.append([label, mesh.get_path_name() if mesh else None,
                        *[round(x, 4) for x in transform(c.get_instance_transform(i, world_space=True))]])
    rows.sort(); instances.sort(); labels.sort()
    return {'actor_labels': labels, 'mesh_components': rows, 'instances': len(instances),
        'instance_sha256': hashlib.sha256(json.dumps(instances, separators=(',', ':')).encode()).hexdigest(),
        'instance_collision_modes': modes}


def target_components():
    result = []
    for actor in actors.get_all_level_actors():
        if actor.actor_has_tag('RoadShoulder'):
            result += actor.get_components_by_class(unreal.StaticMeshComponent)
    if len(result) != 1: raise RuntimeError('Expected exactly one shoulder in the local level')
    return result


def work():
    try:
        assert json.loads((draft/'drainage_mask_audit.json').read_text())['passed']
        assert all(sha(p) == expected for p, expected in v['input_sha256'].items())
        assert sha(v['mask_file']) == v['mask_sha256']
        for path in [tile['map'], v['material_asset'], v['texture_asset']]:
            if assets.does_asset_exist(path): raise RuntimeError('Preserve existing asset '+path)
        if not levels.load_level(tile['drainage_parent_map']): raise RuntimeError('Parent load failed')
        parent_state = snapshot(); journal['parent_state'] = parent_state; save()
        source = target_components()[0].get_material(0)
        if not isinstance(source, unreal.Material): raise RuntimeError('Expected source material rather than an instance')
        journal['source_material'] = source.get_path_name()
        source_file = asset_file(source.get_path_name().split('.')[0], '.uasset')
        before[str(source_file)] = sha(source_file); save()
        task = unreal.AssetImportTask()
        for key, value in {'filename': v['mask_file'], 'destination_path': v['texture_asset'].rsplit('/', 1)[0],
            'destination_name': v['texture_asset'].rsplit('/', 1)[1], 'automated': True, 'save': True,
            'replace_existing': False, 'factory': unreal.TextureFactory()}.items(): task.set_editor_property(key, value)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        texture = unreal.load_asset(v['texture_asset'])
        if not isinstance(texture, unreal.Texture2D): raise RuntimeError('Mask import failed')
        settings = {'srgb': False, 'compression_settings': unreal.TextureCompressionSettings.TC_GRAYSCALE,
            'mip_gen_settings': unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS,
            'filter': unreal.TextureFilter.TF_BILINEAR, 'address_x': unreal.TextureAddress.TA_CLAMP,
            'address_y': unreal.TextureAddress.TA_CLAMP, 'never_stream': True}
        for key, value in settings.items(): texture.set_editor_property(key, value)
        assets.save_loaded_asset(texture)
        mat = assets.duplicate_asset(source.get_path_name().split('.')[0], v['material_asset'])
        if not isinstance(mat, unreal.Material): raise RuntimeError('Material duplication failed')
        base = lib.get_material_property_input_node(mat, unreal.MaterialProperty.MP_BASE_COLOR)
        base_pin = lib.get_material_property_input_node_output_name(mat, unreal.MaterialProperty.MP_BASE_COLOR)
        opacity = lib.get_material_property_input_node(mat, unreal.MaterialProperty.MP_OPACITY_MASK)
        opacity_pin = lib.get_material_property_input_node_output_name(mat, unreal.MaterialProperty.MP_OPACITY_MASK)
        if not base: raise RuntimeError('Expected connected source base color')
        properties = [unreal.MaterialProperty.MP_NORMAL, unreal.MaterialProperty.MP_ROUGHNESS,
            unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET, unreal.MaterialProperty.MP_METALLIC,
            unreal.MaterialProperty.MP_SPECULAR, unreal.MaterialProperty.MP_AMBIENT_OCCLUSION]
        preserved = {str(p): lib.get_material_property_input_node(mat, p) for p in properties}
        physical = mat.get_editor_property('phys_material')
        flags = {key: mat.get_editor_property(key) for key in ['blend_mode', 'opacity_mask_clip_value', 'two_sided']}

        def node(cls): return lib.create_material_expression(mat, cls)
        def connect(a, output, b, pin):
            if not lib.connect_material_expressions(a, output, b, pin): raise RuntimeError('Material pin failed '+pin)
        def custom(code, output_type, names):
            expression = node(unreal.MaterialExpressionCustom)
            expression.set_editor_property('output_type', output_type)
            inputs = []
            for name in names:
                item = unreal.CustomInput(); item.set_editor_property('input_name', name); inputs.append(item)
            expression.set_editor_property('inputs', inputs); expression.set_editor_property('code', code)
            return expression

        position = node(unreal.MaterialExpressionWorldPosition)
        origin = v['uv_origin_UE_xy_cm']; span = v['uv_span_xy_cm']
        uv = custom(f'return (P.xy-float2({origin[0]:.9f},{origin[1]:.9f}))/float2({span[0]:.9f},{span[1]:.9f});',
            unreal.CustomMaterialOutputType.CMOT_FLOAT2, ['P'])
        connect(position, '', uv, 'P')
        sample = node(unreal.MaterialExpressionTextureSample)
        sample.set_editor_property('texture', texture)
        sample.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
        connect(uv, '', sample, 'UVs')
        code = '''struct DrainNoise {
 float hash(float3 x) { x=frac(x*0.1031); x+=dot(x,x.yzx+33.33); return frac((x.x+x.y)*x.z); }
 float noise(float3 p) {
  float3 i=floor(p),f=frac(p); f=f*f*(3-2*f);
  return lerp(lerp(lerp(hash(i),hash(i+float3(1,0,0)),f.x),lerp(hash(i+float3(0,1,0)),hash(i+float3(1,1,0)),f.x),f.y),
   lerp(lerp(hash(i+float3(0,0,1)),hash(i+float3(1,0,1)),f.x),lerp(hash(i+float3(0,1,1)),hash(i+1),f.x),f.y),f.z);
 }
};
DrainNoise n; float3 p=P*0.01;
float broad=n.noise(p*0.8), grain=n.noise(p*24.0), detail=n.noise(p*5.0);
float3 stone=lerp(STONE_DARK,STONE_LIGHT,saturate(0.22+0.46*detail+0.22*grain));
float moss=smoothstep(0.44,0.73,broad+0.10*detail);
return lerp(stone,lerp(MOSS_DARK,MOSS_LIGHT,saturate(0.25+0.5*detail+0.25*grain)),moss*0.86);
'''
        for marker, key in [('STONE_DARK', 'stone_dark_linear'), ('STONE_LIGHT', 'stone_light_linear'),
                            ('MOSS_DARK', 'moss_dark_linear'), ('MOSS_LIGHT', 'moss_light_linear')]:
            code = code.replace(marker, 'float3('+','.join(f'{x:.9f}' for x in cfg[key])+')')
        color = custom(code, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ['P'])
        connect(position, '', color, 'P')
        blend = node(unreal.MaterialExpressionLinearInterpolate)
        connect(base, base_pin, blend, 'A'); connect(color, '', blend, 'B'); connect(sample, 'R', blend, 'Alpha')
        if not lib.connect_material_property(blend, '', unreal.MaterialProperty.MP_BASE_COLOR): raise RuntimeError('Base color connection failed')
        if opacity is None:
            opacity = node(unreal.MaterialExpressionConstant); opacity.set_editor_property('r', 1.0); opacity_pin = ''
        union = node(unreal.MaterialExpressionMax)
        connect(opacity, opacity_pin, union, 'A'); connect(sample, 'R', union, 'B')
        if not lib.connect_material_property(union, '', unreal.MaterialProperty.MP_OPACITY_MASK): raise RuntimeError('Opacity union failed')
        for prop in properties:
            if lib.get_material_property_input_node(mat, prop) != preserved[str(prop)]: raise RuntimeError('Unexpected material output change '+str(prop))
        if mat.get_editor_property('phys_material') != physical: raise RuntimeError('Physical material changed')
        if any(mat.get_editor_property(key) != value for key, value in flags.items()): raise RuntimeError('Material flags changed')
        journal.update(physical_material_preserved=True, other_material_outputs_preserved=True,
            hlsl_code_sha256=hashlib.sha256(code.encode()).hexdigest(),
            texture_settings={key: str(texture.get_editor_property(key)) for key in settings},
            opacity_policy='Maximum(original opacity expression, local grayscale mask); original branch outside mask',
            no_vertex_displacement_added=True)
        lib.recompile_material(mat); assets.save_loaded_asset(mat); save(); yield
        if not levels.new_level_from_template(tile['map'], tile['drainage_parent_map']): raise RuntimeError('Level clone failed')
        if snapshot() != parent_state: raise RuntimeError('Cloning changed actor/mesh/PCG/physics state')
        for component in target_components(): component.set_material(0, mat)
        if snapshot() != parent_state: raise RuntimeError('Material assignment changed physical state')
        components = [c for a in actors.get_all_level_actors() for c in a.get_components_by_class(unreal.StaticMeshComponent)]
        modes = [(c.get_collision_enabled(), c.get_collision_profile_name()) for c in components]
        try:
            for component in components: component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            terrain = json.loads(unreal.LidarTerrainLibrary.verify_lidar_world_tile(tile['heightmap'], tile['holes']))
        finally:
            for component, (enabled, profile) in zip(components, modes):
                component.set_collision_enabled(enabled); component.set_collision_profile_name(profile)
        journal['native_terrain_readback'] = terrain; save()
        if not terrain['passed']: raise RuntimeError('Native height/hole mismatch')
        if snapshot() != parent_state: raise RuntimeError('Terrain readback changed component profiles')
        if not levels.save_current_level(): raise RuntimeError('Level save failed')
        save(); yield
        if not levels.new_level('/Temp/DrainageReload_'+build): raise RuntimeError('Unload failed')
        if not levels.load_level(tile['map']): raise RuntimeError('Reload failed')
        state = snapshot(); journal['reload_state'] = state
        if state != parent_state: raise RuntimeError('Save/reload changed geometry/PCG/physics')
        if any(c.get_material(0).get_path_name() != mat.get_path_name() for c in target_components()): raise RuntimeError('Material override not persisted')
        texture = unreal.load_asset(v['texture_asset'])
        if any(texture.get_editor_property(key) != expected for key, expected in settings.items()): raise RuntimeError('Texture settings not persisted')
        journal.update(saved_and_reloaded=True, geometry_and_pcg_preserved=True,
            texture_settings_persisted=True, protected_files_unchanged=all(sha(p) == expected for p, expected in before.items()))
        if not journal['protected_files_unchanged']: raise RuntimeError('Protected parent file changed')
        journal.update(all_imported=True, ended_unix=time.time()); save()
        (draft/'import_report.json').write_text(json.dumps({'build_id': build, 'manifest': str(manifest_path),
            'all_imported': True, 'journal': str(journal_path), 'activated': False,
            'geometry_and_physics_changed': False, 'native_pcg_preserved': True,
            'actual_rendering_review_complete': False}, indent=2))
        unreal.log('DRAINAGE_SURFACE_IMPORTED '+build)
    except BaseException as error:
        journal.update(error=repr(error), ended_unix=time.time(),
            protected_files_unchanged=all(sha(p) == expected for p, expected in before.items()))
        save(); raise


save()
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
