"""Create the persistent full-territory scene without replacing the tested sample."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir()).resolve().parent
data = json.loads((root / 'Unreal/Content/Data/circuit_world.json').read_text())
assert len(data['tiles']) == 113
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
path = '/Game/Maps/CircuitoSoffumbergo'
if unreal.EditorAssetLibrary.does_asset_exist(path):
    raise RuntimeError('Persistent map already exists; preserving edited scene')
levels.new_level(path)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
world.get_world_settings().set_editor_property('default_game_mode', unreal.LabGameMode)
streaming = actors.spawn_actor_from_class(unreal.CircuitTerrainWorld, unreal.Vector())
streaming.set_actor_label('Territorio_LiDAR_a_settori')
# Keep the previously tested physical spawn until the engineered road supplies
# a verified start. This map is initially terrain only, not a finished circuit.
spawn = json.loads((root / 'parameters/terrain_spawn.json').read_text())
actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(*spawn['position_cm']), unreal.Rotator(0, spawn['yaw_deg'], 0))
sun = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 10000), unreal.Rotator(-36, -48, 0))
sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property('intensity', 55000)
sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 10000))
sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property('real_time_capture', True)
actors.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector())
exposure = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
exposure.set_editor_property('unbound', True)
settings = exposure.get_editor_property('settings')
settings.set_editor_property('override_auto_exposure_method', True)
settings.set_editor_property('auto_exposure_method', unreal.AutoExposureMethod.AEM_MANUAL)
settings.set_editor_property('override_auto_exposure_apply_physical_camera_exposure', True)
settings.set_editor_property('auto_exposure_apply_physical_camera_exposure', False)
settings.set_editor_property('override_auto_exposure_bias', True)
settings.set_editor_property('auto_exposure_bias', -13.0)
exposure.set_editor_property('settings', settings)
levels.save_current_level()
# Dynamic map references are strings, so explicitly include every source map.
config = root / 'Unreal/Config/DefaultGame.ini'
text = config.read_text()
for map_path in [path] + [t['map'] for t in data['tiles']]:
    line = '+MapsToCook=(FilePath="' + map_path + '")'
    if line not in text:
        text += '\n' + line
config.write_text(text + '\n')
(root / 'results/circuit_scene_setup.json').write_text(json.dumps({
    'map': path, 'terrain_tiles': len(data['tiles']), 'spawn': spawn,
    'road_present': False, 'vegetation_present': False,
    'default_sample_preserved': True, 'runtime_streaming_verified': False}, indent=2))
unreal.log('CIRCUIT_SCENE_CREATED ' + path)
