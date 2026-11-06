"""Enable the real vehicle in the LiDAR map and set inspection cameras/light."""
import json
from pathlib import Path
import unreal
root=Path(unreal.Paths.project_dir()).resolve().parent
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels.load_level('/Game/Maps/ValleLiDAR')
spawn=json.loads((root/'parameters/terrain_spawn.json').read_text())
all_actors=actors.get_all_level_actors()
for actor in all_actors:
    if isinstance(actor,unreal.PlayerStart):actors.destroy_actor(actor)
position=unreal.Vector(*spawn['position_cm'])
start=actors.spawn_actor_from_class(unreal.PlayerStart,position,unreal.Rotator(0,spawn['yaw_deg'],0))
start.set_actor_label('Partenza_prova_terreno_LiDAR')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
world.get_world_settings().set_editor_property('default_game_mode',unreal.LabGameMode)
for actor in all_actors:
    if isinstance(actor,unreal.DirectionalLight):
        actor.set_actor_rotation(unreal.Rotator(-36,-48,0),False)
        actor.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property('intensity',55000)
    if isinstance(actor,unreal.SkyLight):
        component=actor.get_component_by_class(unreal.SkyLightComponent)
        component.set_editor_property('real_time_capture',True)
volumes=[a for a in all_actors if isinstance(a,unreal.PostProcessVolume)]
exposure=volumes[0] if volumes else actors.spawn_actor_from_class(unreal.PostProcessVolume,unreal.Vector())
exposure.set_actor_label('Esposizione_diurna_provvisoria')
exposure.set_editor_property('unbound',True)
settings=exposure.get_editor_property('settings')
settings.set_editor_property('override_auto_exposure_method',True)
settings.set_editor_property('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL)
settings.set_editor_property('override_auto_exposure_apply_physical_camera_exposure',True)
settings.set_editor_property('auto_exposure_apply_physical_camera_exposure',False)
settings.set_editor_property('override_auto_exposure_bias',True)
settings.set_editor_property('auto_exposure_bias',-13.0)
exposure.set_editor_property('settings',settings)
for name in ['M_Bark','M_Leaf']:
    material=unreal.load_asset('/Game/Vegetation/'+name)
    unreal.MaterialEditingLibrary.set_material_usage(material,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material)
camera=actors.spawn_actor_from_class(unreal.CameraActor,unreal.Vector(30500,33000,18500))
camera.set_actor_label('Vista_insieme_terreno')
target=unreal.Vector(12600,12600,1500)
rotation=unreal.MathLibrary.find_look_at_rotation(camera.get_actor_location(),target)
camera.set_actor_rotation(rotation,False)
camera.get_component_by_class(unreal.CameraComponent).set_editor_property('field_of_view',52)
unreal.EditorLevelLibrary.set_level_viewport_camera_info(camera.get_actor_location(),rotation)
levels.save_current_level()
(root/'results/terrain_play_setup.json').write_text(json.dumps({'spawn':spawn,'map':'/Game/Maps/ValleLiDAR','game_mode':'LabGameMode','synthetic_ground_disabled':True,'surface_is_bare_lidar':True},indent=2))
unreal.log('LIDAR_PLAY_SETUP saved')
