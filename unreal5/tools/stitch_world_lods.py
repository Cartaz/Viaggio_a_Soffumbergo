"""Share native edge LOD evaluation across independent geographic Landscapes.

UE 5.8 LandscapeProxy.h: LODGroupKey is explicitly provided for matching
border LODs across separate Landscapes. All tiles have the same resolution,
rotation and XY scale, as required by LandscapeRender.cpp.
"""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir()).resolve().parent
m=json.loads((root/'terrain/world_tiles/manifest.json').read_text())
proof=json.loads((root/'results/world_tiles_import.json').read_text())
assert proof['all_imported_and_verified']
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report={'lod_group_key':20261022,'tiles':[],'passed':False}
for t in m['tiles']:
    if not levels.load_level(t['map']):raise RuntimeError(t['map'])
    terrain=next(a for a in actors.get_all_level_actors() if isinstance(a,unreal.Landscape))
    terrain.set_editor_property('lod_group_key',20261022)
    levels.save_current_level()
    verification=json.loads(unreal.LidarTerrainLibrary.verify_lidar_world_tile(t['heightmap'],t['holes']))
    if not verification['passed']:raise RuntimeError('Terrain changed: '+t['id'])
    report['tiles'].append({'id':t['id'],'lod_group_key':terrain.get_editor_property('lod_group_key'),
                            'height_and_collision_unchanged':verification['passed']})
    unreal.SystemLibrary.collect_garbage()
report['passed']=len(report['tiles'])==113 and all(t['lod_group_key']==20261022 for t in report['tiles'])
(root/'results/world_lod_stitching.json').write_text(json.dumps(report,indent=2))
unreal.log('WORLD_LOD_GROUP_COMPLETE '+str(report['passed']))
