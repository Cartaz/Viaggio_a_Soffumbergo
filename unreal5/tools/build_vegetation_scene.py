"""Native UE foliage authoring + actual PCG generation on the LiDAR Landscape."""
import hashlib
import json
import time
from pathlib import Path
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve().parent
LEVELS=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
TOOLS=unreal.AssetToolsHelpers.get_asset_tools()
LEVELS.load_level('/Game/Maps/ValleLiDAR')
terrain_report=json.loads(unreal.LidarTerrainLibrary.verify_lidar_landscape(str(ROOT/'terrain/valle_first/Valle_505.r16'),505))
(ROOT/'results/landscape_collision.json').write_text(json.dumps(terrain_report,indent=2))
if not terrain_report['passed']:
    raise RuntimeError('LiDAR Landscape readback/collision gate failed; see landscape_collision.json')

def material(name,color,foliage=False):
    path='/Game/Vegetation/'+name
    existing=unreal.load_asset(path)
    if existing:return existing
    mat=TOOLS.create_asset(name,'/Game/Vegetation',unreal.Material,unreal.MaterialFactoryNew())
    mat.set_editor_property('two_sided',True)
    if foliage:mat.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    lib=unreal.MaterialEditingLibrary
    def rgb(values,x,y):
        node=lib.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector,x,y)
        node.set_editor_property('constant',unreal.LinearColor(*values,1))
        return node
    a=rgb(color,-600,0);b=rgb([c*1.55 for c in color],-600,130)
    random=lib.create_material_expression(mat,unreal.MaterialExpressionPerInstanceRandom,-600,260)
    mix=lib.create_material_expression(mat,unreal.MaterialExpressionLinearInterpolate,-250,0)
    lib.connect_material_expressions(a,'',mix,'A');lib.connect_material_expressions(b,'',mix,'B')
    lib.connect_material_expressions(random,'',mix,'Alpha')
    lib.connect_material_property(mix,'',unreal.MaterialProperty.MP_BASE_COLOR)
    rough=lib.create_material_expression(mat,unreal.MaterialExpressionConstant,-250,170)
    rough.set_editor_property('r',0.78)
    lib.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    if foliage:
        sub=rgb([c*0.6 for c in color],-250,320)
        lib.connect_material_property(sub,'',unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
    lib.recompile_material(mat);unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat

material('M_Bark',[0.095,0.058,0.028])
material('M_Leaf',[0.065,0.16,0.025],True)
ground=material('M_LidarGround',[0.12,0.15,0.055])
landscape=next(a for a in ACTORS.get_all_level_actors() if isinstance(a,unreal.Landscape))
landscape.set_editor_property('landscape_material',ground)
meshes={}
for name,seed,kind in [('Tree_A',103,0),('Tree_B',214,0),('Tree_C',325,0),('Shrub_A',436,1),('Shrub_B',547,1),('Grass',658,2)]:
    mesh=unreal.LidarTerrainLibrary.create_procedural_foliage('/Game/Vegetation/SM_'+name,seed,kind)
    if not mesh:raise RuntimeError('Foliage generation failed: '+name)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    meshes[name]=mesh

info=json.loads((ROOT/'terrain/valle_first/vegetation_mask.json').read_text())
mask_path='/Game/Procedural/DA_VegetationMask'
mask=unreal.load_asset(mask_path)
if not mask:
    factory=unreal.DataAssetFactory();factory.set_editor_property('data_asset_class',unreal.LidarVegetationMask)
    mask=TOOLS.create_asset('DA_VegetationMask','/Game/Procedural',unreal.LidarVegetationMask,factory)
mask.set_editor_property('width',info['width']);mask.set_editor_property('height',info['height'])
mask.set_editor_property('spacing_cm',info['spacing_cm']);mask.set_editor_property('origin_cm',unreal.Vector())
mask.set_editor_property('cells',list((ROOT/'terrain/valle_first/vegetation_mask.bin').read_bytes()))
mask.set_editor_property('provenance',json.dumps(info))
unreal.EditorAssetLibrary.save_loaded_asset(mask)

graph_path='/Game/Procedural/PCG_ValleVegetazione'
graph=unreal.load_asset(graph_path)
if not graph:
    graph=TOOLS.create_asset('PCG_ValleVegetazione','/Game/Procedural',unreal.PCGGraph,unreal.PCGGraphFactory())
    source,_=graph.add_node_of_type(unreal.PCGGetLandscapeSettings)
    for name,density,extent,cover,slope,scale,cull,choices in [
        ('trees',0.012,250,1,40,(0.8,1.15),30000,['Tree_A','Tree_B','Tree_C']),
        ('shrubs',0.025,80,1,48,(0.65,1.15),13000,['Shrub_A','Shrub_B']),
        ('grass',0.14,25,2,35,(0.7,1.2),9000,['Grass'])]:
        sample,s=graph.add_node_of_type(unreal.PCGSurfaceSamplerSettings)
        s.set_editor_property('points_per_squared_meter',density);s.set_editor_property('point_extents',unreal.Vector(extent,extent,extent))
        s.set_editor_property('seed',20261022)
        filter_node,f=graph.add_node_of_type(unreal.PCGLidarVegetationSettings)
        f.set_editor_property('mask',mask);f.set_editor_property('required_class',cover)
        f.set_editor_property('max_slope_degrees',slope);f.set_editor_property('min_scale',scale[0]);f.set_editor_property('max_scale',scale[1])
        spawn,sp=graph.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
        sp.set_mesh_selector_type(unreal.PCGMeshSelectorWeighted)
        sp.set_editor_property('synchronous_load',True)
        selector=sp.get_editor_property('mesh_selector_parameters')
        entries=[]
        for choice in choices:
            entry=unreal.PCGMeshSelectorWeightedEntry()
            descriptor=entry.get_editor_property('descriptor')
            descriptor.set_editor_property('static_mesh',meshes[choice])
            descriptor.set_editor_property('instance_start_cull_distance',int(cull*0.8))
            descriptor.set_editor_property('instance_end_cull_distance',cull)
            descriptor.set_editor_property('cast_shadow',name!='grass')
            entry.set_editor_property('descriptor',descriptor);entry.set_editor_property('weight',1);entries.append(entry)
        selector.set_editor_property('mesh_entries',entries)
        graph.add_edge(source,'Out',sample,'Surface');graph.add_edge(sample,'Out',filter_node,'In')
        graph.add_edge(filter_node,'Out',spawn,'In');graph.add_edge(spawn,'Out',graph.get_output_node(),'Out')
    unreal.EditorAssetLibrary.save_loaded_asset(graph)

areas=[a for a in ACTORS.get_all_level_actors() if isinstance(a,unreal.LidarProceduralArea)]
if len(areas)>1:raise RuntimeError('Unexpected duplicate PCG areas')
area=areas[0] if areas else ACTORS.spawn_actor_from_class(unreal.LidarProceduralArea,unreal.Vector(12600,12600,0))
area.set_actor_label('Vegetazione_PCG_LiDAR_OSM')
component=area.get_component_by_class(unreal.PCGComponent)
component.set_graph(graph);component.set_editor_property('seed',20261022)
LEVELS.save_current_level()

def snapshot():
    rows=[];counts={}
    for instance in area.get_components_by_class(unreal.InstancedStaticMeshComponent):
        mesh=instance.get_editor_property('static_mesh')
        if not mesh:continue
        name=mesh.get_name();count=instance.get_instance_count();counts[name]=counts.get(name,0)+count
        for i in range(count):
            t=instance.get_instance_transform(i,world_space=True)
            p=t.translation;q=t.rotation;s=t.scale3d
            rows.append([name,*[round(v,4) for v in [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]]])
    rows.sort()
    return {'counts':counts,'instances':len(rows),'sha256':hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest(),'rows':rows}

started=time.monotonic();state={'stage':0,'ready':False,'runs':[]}
def generated(_):state['ready']=True
component.on_pcg_graph_generated_external.add_callable(generated)
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
def tick(_):
    try:
        if time.monotonic()-started>150:raise TimeoutError('PCG generation did not complete')
        if not state['ready']:return
        state['ready']=False
        data=snapshot();state['runs'].append({k:v for k,v in data.items() if k!='rows'})
        stage=state['stage'];unreal.log('PCG_PASS '+json.dumps(state['runs'][-1]))
        if data['instances']==0:raise RuntimeError('PCG generated no vegetation')
        if stage==0:
            state['baseline']=data
        elif stage==1 and data['sha256']!=state['baseline']['sha256']:
            raise RuntimeError('Regeneration with the same seed changed the instances')
        elif stage==2 and data['sha256']==state['baseline']['sha256']:
            raise RuntimeError('Changing the seed did not affect generation')
        elif stage==3:
            assert data['sha256']==state['baseline']['sha256'], 'Restoring the seed did not restore vegetation'
            raw=(ROOT/'terrain/valle_first/vegetation_mask.bin').read_bytes()
            violations=[]
            for row in data['rows']:
                name,x,y=row[:3];ix=round(x/50);iy=round(y/50)
                expected=2 if 'Grass' in name else 1
                if not(0<=ix<505 and 0<=iy<505) or raw[iy*505+ix]!=expected:violations.append(row)
            assert not violations,'Vegetation outside mapped allowed cover'
            LEVELS.save_current_level()
            report={'engine':unreal.SystemLibrary.get_engine_version(),'landscape_gate':terrain_report['passed'],
                    'runs':state['runs'],'same_seed_identical':True,'changed_seed_changes_output':True,
                    'restored_seed_identical':True,'mask_violations':len(violations),'final_counts':data['counts'],
                    'elapsed_s':time.monotonic()-started,'vegetation_is_procedural_not_observed_individual_trees':True,
                    'artistic_quality_approved':False,'fps_target_verified':False}
            (ROOT/'results/vegetation_generation.json').write_text(json.dumps(report,indent=2))
            unreal.log('VEGETATION_VERIFIED '+json.dumps(report))
            unreal.unregister_slate_post_tick_callback(handle)
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            return
        state['stage']+=1
        component.set_editor_property('seed',20261023 if state['stage']==2 else 20261022)
        component.generate_local(True)
    except Exception as exc:
        (ROOT/'results/vegetation_failure.json').write_text(json.dumps({'error':str(exc),'stage':state['stage']}))
        unreal.log_error(str(exc));unreal.unregister_slate_post_tick_callback(handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
handle=unreal.register_slate_post_tick_callback(tick)
component.generate_local(True)
