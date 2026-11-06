"""Reopen the saved Landscape, repair the initial PCG source and inspect it."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir()).resolve().parent
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
levels.load_level('/Game/Maps/ValleLiDAR')
graph=unreal.load_asset('/Game/Procedural/PCG_VegetazioneLiDAR')
nodes=list(graph.get_editor_property('nodes'))
sampler=next(n for n in nodes if isinstance(n.get_settings(),unreal.PCGSurfaceSamplerSettings))
def pin(node,side,label):
    return next(p for p in node.get_editor_property(side+'_pins') if str(p.get_editor_property('properties').label)==label)
if not pin(sampler,'input','Surface').get_editor_property('edges'):
    getter,_=graph.add_node_of_type(unreal.PCGGetLandscapeSettings)
    graph.add_edge(getter,'Out',sampler,'Surface')
assert pin(sampler,'input','Surface').get_editor_property('edges'), 'PCG source not connected'
assert pin(sampler,'output','Out').get_editor_property('edges'), 'PCG output not connected'
unreal.EditorAssetLibrary.save_loaded_asset(graph)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
landscapes=[a for a in actors if isinstance(a,unreal.Landscape)]
assert len(landscapes)==1, 'Expected one saved Landscape'
report=json.loads((root/'results/initial_unreal_setup.json').read_text())
report.update({'saved_map_reopened':True,'pcg_landscape_source_connected':True,
               'pcg_sampler_output_connected':True,'pcg_graph_nodes':len(graph.get_editor_property('nodes'))})
(root/'results/initial_unreal_setup.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('LIDAR_VERIFIED '+json.dumps(report))
