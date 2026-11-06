"""Import generated road and graded Landscape maps; preserve raw source maps."""
import json
import os
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir()).resolve().parent
draft_manifest=os.environ.get('SOFFUMBERGO_DRAFT_MANIFEST')
pointer={'manifest':draft_manifest} if draft_manifest else json.loads((root/'parameters/current_road_design.json').read_text())
m=json.loads(Path(pointer['manifest']).read_text())
draft_dir=root/'results/road_drafts'/m['build_id']
if draft_manifest:
    draft_dir.mkdir(parents=True,exist_ok=True)
    unreal.log('DRAFT_CONTENT_PATH '+unreal.Paths.project_content_dir())
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assets=unreal.EditorAssetLibrary
tools=unreal.AssetToolsHelpers.get_asset_tools()
journal_path=root/('results/road_import_'+m['build_id']+'.json')
journal=json.loads(journal_path.read_text()) if journal_path.exists() else {'build_id':m['build_id'],'tiles':{}}

materials={}
for kind,color,roughness,friction in [('asphalt',(.025,.03,.035),.92,.9),('shoulder',(.15,.12,.075),.98,.75),
                                        ('concrete',(.28,.27,.24),.9,.8),('metal',(.32,.35,.37),.48,.65)]:
    path='/Game/World/Materials/M_Road_'+kind
    mat=unreal.load_asset(path) if assets.does_asset_exist(path) else None
    if mat is None:
        mat=tools.create_asset('M_Road_'+kind,'/Game/World/Materials',unreal.Material,unreal.MaterialFactoryNew())
        if kind in ['asphalt','shoulder']:mat.set_editor_property('two_sided',True)
        c=unreal.MaterialEditingLibrary.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector)
        c.set_editor_property('constant',unreal.LinearColor(*color,1))
        r=unreal.MaterialEditingLibrary.create_material_expression(mat,unreal.MaterialExpressionConstant);r.set_editor_property('r',roughness)
        unreal.MaterialEditingLibrary.connect_material_property(c,'',unreal.MaterialProperty.MP_BASE_COLOR)
        unreal.MaterialEditingLibrary.connect_material_property(r,'',unreal.MaterialProperty.MP_ROUGHNESS)
        phys=tools.create_asset('PM_Road_'+kind,'/Game/World/Materials',unreal.PhysicalMaterial,unreal.PhysicalMaterialFactoryNew())
        phys.set_editor_property('friction',friction);phys.set_editor_property('restitution',0)
        mat.set_editor_property('phys_material',phys)
        unreal.MaterialEditingLibrary.recompile_material(mat)
        assets.save_loaded_asset(phys);assets.save_loaded_asset(mat)
    materials[kind]=mat.get_path_name()

for tile in m['tiles']:
    if not tile.get('engineering_terrain'):continue
    previous=journal['tiles'].get(tile['id'])
    if assets.does_asset_exist(tile['map']):
        if not previous or previous['height_sha256']!=tile['height_sha256']:raise RuntimeError('Preserving untracked map '+tile['map'])
        if previous.get('saved_complete'):continue
        levels.load_level(tile['map'])
        for actor in actors.get_all_level_actors():
            if isinstance(actor,(unreal.Landscape,unreal.StaticMeshActor)):actors.destroy_actor(actor)
    else:
        journal['tiles'][tile['id']]={'height_sha256':tile['height_sha256'],'saved_complete':False}
        journal_path.write_text(json.dumps(journal,indent=2))
        levels.new_level(tile['map'])
    landscape=unreal.LidarTerrainLibrary.import_lidar_world_tile(tile['heightmap'],tile['holes'],unreal.Vector(*tile['location_cm']),tile['z_scale'])
    if landscape is None:raise RuntimeError('Landscape import failed '+tile['id'])
    landscape.set_actor_label('Terreno_derivato_'+tile['id'])
    landscape.set_editor_property('lod_group_key',20261022)
    terrain_check=json.loads(unreal.LidarTerrainLibrary.verify_lidar_world_tile(tile['heightmap'],tile['holes']))
    if not terrain_check['passed']:raise RuntimeError('Derived terrain verification failed '+str(terrain_check))
    record={'map':tile['map'],'height_sha256':tile['height_sha256'],'terrain_before_road':terrain_check,'meshes':[],'saved_complete':False}
    journal['tiles'][tile['id']]=record
    for mesh_info in [v for v in m['meshes'] if v['tile']==tile['id']]:
        mesh=unreal.LidarTerrainLibrary.create_circuit_mesh(mesh_info['source'],mesh_info['asset'],materials[mesh_info['kind']])
        if mesh is None:raise RuntimeError('Road mesh creation failed '+mesh_info['id'])
        assets.save_loaded_asset(mesh)
        actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*mesh_info['location_cm']))
        component=actor.get_component_by_class(unreal.StaticMeshComponent)
        component.set_static_mesh(mesh)
        component.set_collision_profile_name('BlockAll')
        component.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        actor.set_actor_label(mesh_info['id'])
        actor.set_editor_property('tags',['RoadSurface' if mesh_info['kind']=='asphalt' else 'RoadShoulder' if mesh_info['kind']=='shoulder' else 'BridgeStructure'])
        record['meshes'].append(mesh_info['id'])
    levels.save_current_level();record['saved_complete']=True
    journal['all_imported']=len(journal['tiles'])==sum(bool(t.get('engineering_terrain')) for t in m['tiles'])
    journal_path.write_text(json.dumps(journal,indent=2))
    unreal.log('DRIVING_TILE_IMPORTED '+tile['id'])
    unreal.SystemLibrary.collect_garbage()

if not journal.get('all_imported'):raise RuntimeError('Not all driving tiles imported')
runtime={k:m[k] for k in ['build_id','road_survey_points_cm','profile_UE_cm','profile_station_m','sectors','spawn']}
runtime['tiles']=[{k:t[k] for k in ['id','map','bounds_xy_cm']} for t in m['tiles']]
scene='/Game/Maps/CircuitoGuidabile'
if draft_manifest:
    current=json.loads(Path(json.loads((root/'parameters/current_road_design.json').read_text())['manifest']).read_text())
    if current['spawn']!=m['spawn']:raise RuntimeError('Separate draft QA needs its own persistent spawn map')
    (draft_dir/'circuit_driving_world.json').write_text(json.dumps(runtime))
    (draft_dir/'import_report.json').write_text(json.dumps({'build_id':m['build_id'],'all_imported':True,
        'journal':str(journal_path),'map':scene,'activated':False,'root_map_modified':False,
        'editor_content_dir':unreal.Paths.project_content_dir()},indent=2))
    unreal.log('DRIVING_DRAFT_IMPORTED '+m['build_id'])
else:
    (root/'Unreal/Content/Data/circuit_driving_world.json').write_text(json.dumps(runtime))
    if not assets.does_asset_exist(scene):
        if not levels.new_level_from_template(scene,'/Game/Maps/CircuitoSoffumbergo'):raise RuntimeError('Could not create driving persistent map')
    levels.load_level(scene)
    for actor in actors.get_all_level_actors():
        if isinstance(actor,unreal.PlayerStart):actors.destroy_actor(actor)
        if isinstance(actor,unreal.SkyAtmosphere):
            actor.get_component_by_class(unreal.SkyAtmosphereComponent).set_editor_property('transform_mode',unreal.SkyAtmosphereTransformMode.PLANET_TOP_AT_COMPONENT_TRANSFORM)
            actor.set_actor_location(unreal.Vector(0,0,-m['origin_ENH_m'][2]*100),False,False)
    spawn=m['spawn']
    actors.spawn_actor_from_class(unreal.PlayerStart,unreal.Vector(*spawn['position_cm']),unreal.Rotator(0,spawn['yaw_deg'],0))
    levels.save_current_level()
    (root/'results/current_road_import.json').write_text(json.dumps({'build_id':m['build_id'],'all_imported':True,'journal':str(journal_path),'map':scene},indent=2))
    unreal.log('DRIVING_WORLD_IMPORTED '+m['build_id'])
