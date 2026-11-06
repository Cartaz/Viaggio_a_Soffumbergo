"""Run with Unreal 5.8 Editor Python after building the editor modules."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir()).resolve().parent
manifest=json.loads((root/'terrain/valle_first/manifest.json').read_text(encoding='utf-8'))
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
map_path='/Game/Maps/ValleLiDAR'
if unreal.EditorAssetLibrary.does_asset_exist(map_path):
    raise RuntimeError('Scene already exists; refusing to overwrite edited work')
levels.new_level(map_path)
terrain=unreal.LidarTerrainLibrary.import_lidar_landscape(
    str(root/'terrain/valle_first/Valle_505.r16'),505,
    manifest['landscape']['xy_scale_cm'],manifest['landscape']['z_scale'],manifest['landscape']['actor_z_cm'])
if terrain is None:
    raise RuntimeError('Landscape import failed')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
world.get_world_settings().set_editor_property('default_game_mode',unreal.GameModeBase)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
sun=actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,10000),unreal.Rotator(-40,-30,0))
sun.set_actor_label('Sole_provvisorio')
actors.spawn_actor_from_class(unreal.SkyLight,unreal.Vector(0,0,10000))
actors.spawn_actor_from_class(unreal.SkyAtmosphere,unreal.Vector())
levels.save_current_level()

graph=unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    'PCG_VegetazioneLiDAR','/Game/Procedural',unreal.PCGGraph,unreal.PCGGraphFactory())
if graph is None:
    raise RuntimeError('PCG graph creation failed')
sampler,settings=graph.add_node_of_type(unreal.PCGSurfaceSamplerSettings)
settings.set_editor_property('points_per_squared_meter',0.02)
settings.set_editor_property('seed',20261022)
settings.set_editor_property('point_extents',unreal.Vector(150,150,150))
getter,getter_settings=graph.add_node_of_type(unreal.PCGGetLandscapeSettings)
graph.add_edge(getter,'Out',sampler,'Surface')
graph.add_edge(sampler,'Out',graph.get_output_node(),'Out')
surface_pin=next(p for p in sampler.get_editor_property('input_pins') if str(p.get_editor_property('properties').label)=='Surface')
if not surface_pin.get_editor_property('edges'):
    raise RuntimeError('PCG Landscape source is not connected')
unreal.EditorAssetLibrary.save_loaded_asset(graph)

# The graph samples the landscape only. Exclusion/coverage data and approved
# foliage meshes are required before this becomes a vegetation generator.
report={
 'engine':unreal.SystemLibrary.get_engine_version(),'map':map_path,
 'landscape_actor':terrain.get_path_name(),'landscape_import_verified':True,
 'pcg_graph':graph.get_path_name(),'pcg_sampling_graph_created':True,
 'pcg_generation_executed':False,'vegetation_spawned':False,
 'collision_verified':False,'gameplay_verified':False,
 'scope':'252x252m exact LiDAR crop, diagnostic materials/lighting; not final P3'
}
(root/'results/initial_unreal_setup.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('SOFFUMBERGO_SETUP '+json.dumps(report))
