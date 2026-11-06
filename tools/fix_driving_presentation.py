"""Render geographic elevations above the atmosphere's ground and inspect planes."""
import unreal
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels.load_level('/Game/Maps/CircuitoGuidabile')
for actor in actors.get_all_level_actors():
    if isinstance(actor,unreal.SkyAtmosphere):
        component=actor.get_component_by_class(unreal.SkyAtmosphereComponent)
        component.set_editor_property('transform_mode',unreal.SkyAtmosphereTransformMode.PLANET_TOP_AT_COMPONENT_TRANSFORM)
        actor.set_actor_location(unreal.Vector(0,0,-68974),False,False)
levels.save_current_level()
for name in ['asphalt','shoulder']:
    mat=unreal.load_asset('/Game/World/Materials/M_Road_'+name)
    mat.set_editor_property('two_sided',True)
    unreal.MaterialEditingLibrary.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
unreal.log('DRIVING_PRESENTATION_REVIEW_READY')
