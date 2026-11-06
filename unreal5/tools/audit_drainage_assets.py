"""Fresh-process readback of saved material connections and texture settings."""
import hashlib
import json
import os
from pathlib import Path
import time
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve().parent
manifest = Path(os.environ['SOFFUMBERGO_DRAINAGE_MANIFEST'])
output = Path(os.environ['SOFFUMBERGO_DRAINAGE_AUDIT_OUTPUT'])
if output.exists(): raise RuntimeError('Preserve previous native asset audit')
m = json.loads(manifest.read_text()); v = m['drainage_surface']
draft = ROOT/'results/road_drafts'/m['build_id']
imported = json.loads((draft/'drainage_native_import.json').read_text())
lib = unreal.MaterialEditingLibrary


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def native_file(asset, suffix='.uasset'):
    return ROOT/'Unreal/Content'/(asset.split('.')[0].removeprefix('/Game/')+suffix)


paths = [manifest, native_file(v['texture_asset']), native_file(v['material_asset']),
         native_file(imported['source_material']), native_file(next(t['map'] for t in m['tiles'] if t['id'] == v['config']['tile']), '.umap')]
before = {str(p): sha(p) for p in paths}
report = {'build_id': m['build_id'], 'started_unix': time.time(), 'passed': False,
    'rendering': False, 'protected_before': before, 'method': 'Fresh Editor process loads saved material/texture packages; no authoring or save calls.'}
try:
    mat = unreal.load_asset(v['material_asset']); source = unreal.load_asset(imported['source_material'])
    texture = unreal.load_asset(v['texture_asset'])
    assert isinstance(mat, unreal.Material) and isinstance(source, unreal.Material) and isinstance(texture, unreal.Texture2D)
    checks = {}
    settings = {'srgb': False, 'compression_settings': unreal.TextureCompressionSettings.TC_GRAYSCALE,
        'mip_gen_settings': unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS, 'filter': unreal.TextureFilter.TF_BILINEAR,
        'address_x': unreal.TextureAddress.TA_CLAMP, 'address_y': unreal.TextureAddress.TA_CLAMP, 'never_stream': True}
    checks['saved_texture_settings'] = all(texture.get_editor_property(k) == value for k, value in settings.items())
    size = [texture.blueprint_get_size_x(), texture.blueprint_get_size_y()]
    checks['texture_dimensions'] = size == v['texture_size_xy']
    checks['physical_material'] = mat.get_editor_property('phys_material') == source.get_editor_property('phys_material')
    checks['material_flags'] = all(mat.get_editor_property(k) == source.get_editor_property(k) for k in ['blend_mode', 'opacity_mask_clip_value', 'two_sided'])
    def identity(node): return [node.get_name(), node.get_class().get_name()] if node else None
    for prop in [unreal.MaterialProperty.MP_NORMAL, unreal.MaterialProperty.MP_ROUGHNESS,
                 unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET, unreal.MaterialProperty.MP_METALLIC,
                 unreal.MaterialProperty.MP_SPECULAR, unreal.MaterialProperty.MP_AMBIENT_OCCLUSION]:
        checks['unchanged_'+str(prop)] = identity(lib.get_material_property_input_node(mat, prop)) == identity(lib.get_material_property_input_node(source, prop))
    base = lib.get_material_property_input_node(mat, unreal.MaterialProperty.MP_BASE_COLOR)
    opacity = lib.get_material_property_input_node(mat, unreal.MaterialProperty.MP_OPACITY_MASK)
    checks['base_is_lerp'] = isinstance(base, unreal.MaterialExpressionLinearInterpolate)
    checks['opacity_is_maximum'] = isinstance(opacity, unreal.MaterialExpressionMax)
    inputs = lib.get_inputs_for_material_expression(mat, base)
    assert len(inputs) == 3
    old_base = lib.get_material_property_input_node(source, unreal.MaterialProperty.MP_BASE_COLOR)
    checks['original_base_color_branch'] = identity(inputs[0]) == identity(old_base)
    checks['procedural_color_code'] = isinstance(inputs[1], unreal.MaterialExpressionCustom) and hashlib.sha256(str(inputs[1].get_editor_property('code')).encode()).hexdigest() == imported['hlsl_code_sha256']
    sample = inputs[2]
    checks['mask_texture_binding'] = isinstance(sample, unreal.MaterialExpressionTextureSample) and sample.get_editor_property('texture') == texture
    checks['linear_grayscale_sampler'] = sample.get_editor_property('sampler_type') == unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE
    opacity_inputs = lib.get_inputs_for_material_expression(mat, opacity)
    old_opacity = lib.get_material_property_input_node(source, unreal.MaterialProperty.MP_OPACITY_MASK)
    checks['original_opacity_and_same_mask'] = len(opacity_inputs) == 2 and identity(opacity_inputs[0]) == identity(old_opacity) and opacity_inputs[1] == sample
    uv = [n for n in lib.get_inputs_for_material_expression(mat, sample) if n is not None]
    assert len(uv) == 1 and isinstance(uv[0], unreal.MaterialExpressionCustom)
    origin = v['uv_origin_UE_xy_cm']; span = v['uv_span_xy_cm']
    expected = f'return (P.xy-float2({origin[0]:.9f},{origin[1]:.9f}))/float2({span[0]:.9f},{span[1]:.9f});'
    checks['saved_world_uv_mapping'] = uv[0].get_editor_property('code') == expected
    checks['saved_absolute_world_position'] = any(isinstance(n, unreal.MaterialExpressionWorldPosition) for n in lib.get_inputs_for_material_expression(mat, uv[0]))
    checks['protected_files_unchanged'] = all(sha(path) == expected for path, expected in before.items())
    report.update(checks=checks, texture_size_xy=size, passed=all(checks.values()))
except BaseException as error:
    report['error'] = repr(error)
report['ended_unix'] = time.time(); output.write_text(json.dumps(report, indent=2))
if not report['passed']: raise RuntimeError('Fresh saved-asset audit failed: '+str(report))
unreal.log('DRAINAGE_SAVED_ASSETS_VERIFIED '+m['build_id'])
