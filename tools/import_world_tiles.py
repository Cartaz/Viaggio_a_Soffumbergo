"""Run in Unreal Editor. Import/resume the entire LiDAR mosaic, with native holes.

Existing verified maps are loaded and checked again. Existing maps without a
matching journal entry are preserved and rejected rather than overwritten.
SOFFUMBERGO_TILE_LIMIT can restrict a diagnostic run; it never marks all imported.
"""
import json
import os
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir()).resolve().parent
manifest = json.loads((root / 'terrain/world_tiles/manifest.json').read_text())
journal_path = root / 'results/world_tiles_import.json'
journal = json.loads(journal_path.read_text()) if journal_path.exists() else {'tiles': {}}
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assets = unreal.EditorAssetLibrary
material_path = '/Game/World/Materials/M_LidarWorld'
material = unreal.load_asset(material_path) if assets.does_asset_exist(material_path) else None
if material is None:
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'M_LidarWorld', '/Game/World/Materials', unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
    color = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionConstant3Vector)
    color.set_editor_property('constant', unreal.LinearColor(0.12, 0.19, 0.055, 1))
    roughness = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionConstant)
    roughness.set_editor_property('r', 0.94)
    visibility = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionLandscapeVisibilityMask)
    unreal.MaterialEditingLibrary.connect_material_property(color, '', unreal.MaterialProperty.MP_BASE_COLOR)
    unreal.MaterialEditingLibrary.connect_material_property(roughness, '', unreal.MaterialProperty.MP_ROUGHNESS)
    unreal.MaterialEditingLibrary.connect_material_property(visibility, '', unreal.MaterialProperty.MP_OPACITY_MASK)
    unreal.MaterialEditingLibrary.recompile_material(material)
    assets.save_loaded_asset(material)

limit = int(os.environ.get('SOFFUMBERGO_TILE_LIMIT', '0'))
for index, tile in enumerate(manifest['tiles']):
    if limit and index >= limit:
        break
    previous = journal['tiles'].get(tile['id'])
    exists = assets.does_asset_exist(tile['map'])
    if exists:
        if not previous or previous.get('height_sha256') != tile['height_sha256'] or previous.get('holes_sha256') != tile['holes_sha256']:
            raise RuntimeError('Preserving untracked or modified map: ' + tile['map'])
        if not levels.load_level(tile['map']):
            raise RuntimeError('Could not reopen ' + tile['map'])
        if not previous.get('verification', {}).get('passed'):
            # Only rebuild our own failed generated landscape. No arbitrary map
            # replacement; source hashes above must match the recorded import.
            actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            for actor in actors.get_all_level_actors():
                if isinstance(actor, unreal.Landscape):
                    actors.destroy_actor(actor)
            exists = False
    if not exists:
        if not previous and not levels.new_level(tile['map']):
            raise RuntimeError('Could not create ' + tile['map'])
        terrain = unreal.LidarTerrainLibrary.import_lidar_world_tile(
            tile['heightmap'], tile['holes'], unreal.Vector(*tile['location_cm']), tile['z_scale'])
        if terrain is None:
            raise RuntimeError('Native Landscape import failed: ' + tile['id'])
        terrain.set_actor_label('LiDAR_' + tile['id'])
        terrain.set_editor_property('lod_group_key', 20261022)
        terrain.set_editor_property('static_lighting_lod', 2)
        levels.save_current_level()
        # Reopen the saved package so the test covers serialized collision too.
        levels.load_level(tile['map'])
    verification = json.loads(unreal.LidarTerrainLibrary.verify_lidar_world_tile(tile['heightmap'], tile['holes']))
    record = {'map': tile['map'], 'height_sha256': tile['height_sha256'], 'holes_sha256': tile['holes_sha256'],
              'verification': verification}
    journal['tiles'][tile['id']] = record
    journal['expected_tiles'] = len(manifest['tiles'])
    journal['engine'] = unreal.SystemLibrary.get_engine_version()
    journal['all_imported_and_verified'] = len(journal['tiles']) == len(manifest['tiles']) and all(
        item['verification']['passed'] for item in journal['tiles'].values())
    journal['scope'] = 'Native saved Landscape heights and sampled collision/NoData; not streaming or driving validation'
    journal_path.write_text(json.dumps(journal, indent=2), encoding='utf-8')
    unreal.log('WORLD_TILE_VERIFIED ' + tile['id'] + ' ' + json.dumps(verification))
    if not verification.get('passed'):
        raise RuntimeError('Saved terrain verification failed: ' + tile['id'])
    unreal.SystemLibrary.collect_garbage()
unreal.log('WORLD_TILE_IMPORT_COMPLETE ' + str(journal.get('all_imported_and_verified')))
