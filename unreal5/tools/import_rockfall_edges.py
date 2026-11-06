"""Clone affected levels and append native wire/curb actors; preserve parents."""
import hashlib
import json
import os
from pathlib import Path
import time
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve().parent
manifest_path=Path(os.environ['SOFFUMBERGO_ROCKFALL_MANIFEST'])
m=json.loads(manifest_path.read_text());s=m['rockfall_edges'];build=m['build_id']
draft=ROOT/'results/road_drafts'/build
audit=json.loads((draft/'structure_geometry_audit.json').read_text())
if audit.get('build_id')!=build or not audit.get('passed'):raise RuntimeError('Matching passing geometry audit required')
parent=Path(s['parent_draft']);parent_import=json.loads((parent/'import_report.json').read_text())
assert parent_import['all_imported'] and parent_import['build_id']==s['parent_build_id']
old=json.loads(Path(s['parent_manifest']).read_text())
assets=unreal.EditorAssetLibrary
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
lib=unreal.MaterialEditingLibrary

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def asset_file(path,suffix):return ROOT/'Unreal/Content'/(path.removeprefix('/Game/')+suffix)

protected=[ROOT/'parameters/current_road_design.json',ROOT/'Unreal/Content/Data/circuit_driving_world.json',
 ROOT/'Unreal/Content/Data/circuit_itinerary.json',ROOT/'Unreal/Content/Maps/CircuitoGuidabile.umap']
protected += [asset_file(t['map'],'.umap') for t in old['tiles']]
protected += [asset_file(r['asset'],'.uasset') for r in old['meshes']]
protected += [ROOT/'Unreal/Content/World/Materials'/('M_Road_'+kind+'.uasset') for kind in ['metal','concrete']]
before={str(p):sha(p) for p in protected}
attempt=os.environ.get('SOFFUMBERGO_ROCKFALL_ATTEMPT','v1')
if not attempt.replace('_','').isalnum():raise ValueError('Unsafe attempt id')
journal_path=draft/('rockfall_native_import_'+attempt+'.json')
if journal_path.exists():raise RuntimeError('Preserve previous import evidence')
journal={'build_id':build,'parent_build_id':s['parent_build_id'],'started_unix':time.time(),
 'protected_before':before,'tiles':{},'all_imported':False}
journal_path.write_text(json.dumps(journal,indent=2))
materials={}
for kind,color,roughness,metallic,parent_kind in [
 ('rockfall_net',(.10,.12,.13),.72,.5,'metal'),('rockfall_curb',(.17,.19,.12),.96,0.,'concrete')]:
 path='/Game/World/Driving/F_'+build+'/Materials/M_'+kind
 if assets.does_asset_exist(path):raise RuntimeError('Preserving untracked existing material '+path)
 folder,name=path.rsplit('/',1)
 mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
 old_material=unreal.load_asset('/Game/World/Materials/M_Road_'+parent_kind)
 mat.set_editor_property('phys_material',old_material.get_editor_property('phys_material'))
 if kind=='rockfall_net' and s['config'].get('net_representation')=='world_projected_hex_mask':
  params=s['net_material_parameters'];along=params['net_world_along_xy_unit'];radius=params['net_mask_cell_radius_m'];diameter=params['net_mask_wire_diameter_m']
  mat.set_editor_property('two_sided',True);mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
  mat.set_editor_property('opacity_mask_clip_value',params['net_mask_clip'])
  world_position=lib.create_material_expression(mat,unreal.MaterialExpressionWorldPosition)
  mask=lib.create_material_expression(mat,unreal.MaterialExpressionCustom)
  mask.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT1)
  input_position=unreal.CustomInput();input_position.set_editor_property('input_name','P')
  mask.set_editor_property('inputs',[input_position])
  across=params['net_world_uphill_xy_unit'];uphill_weight=params['net_projection_uphill_weight']
  code=f'''float2 along=float2({along[0]:.12f},{along[1]:.12f});
float2 across=float2({across[0]:.12f},{across[1]:.12f});
float3 p=P*0.01;
float2 uv=float2(dot(p.xy,along),(p.z+{uphill_weight:.9f}*dot(p.xy,across))*{(1+uphill_weight**2)**-.5:.12f});
float r={radius:.9f};
float2 period=float2(3.0*r,1.7320508075688772*r);
float2 a=(frac(uv/period+0.5)-0.5)*period;
float2 b=(frac((uv-period*0.5)/period+0.5)-0.5)*period;
float2 q=abs(dot(a,a)<dot(b,b)?a:b);
float d=abs(max(q.y,0.8660254037844386*q.x+0.5*q.y)-0.8660254037844386*r);
return saturate(0.5+({diameter*.5:.9f}-d)/max(fwidth(d),0.00001));'''
  mask.set_editor_property('code',code)
  if not lib.connect_material_expressions(world_position,'',mask,'P'):raise RuntimeError('Missing world projection input')
  if not lib.connect_material_property(mask,'',unreal.MaterialProperty.MP_OPACITY_MASK):raise RuntimeError('Missing procedural net mask')
 c=lib.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector)
 c.set_editor_property('constant',unreal.LinearColor(*color,1))
 lib.connect_material_property(c,'',unreal.MaterialProperty.MP_BASE_COLOR)
 for value,prop in [(roughness,unreal.MaterialProperty.MP_ROUGHNESS),(metallic,unreal.MaterialProperty.MP_METALLIC)]:
  n=lib.create_material_expression(mat,unreal.MaterialExpressionConstant);n.set_editor_property('r',value)
  lib.connect_material_property(n,'',prop)
 lib.recompile_material(mat);assets.save_loaded_asset(mat);materials[kind]=path
journal['material_assets']=materials
changed=[t for t in m['tiles'] if t.get('rockfall_parent_map')]

def trace(world,start,end,ignored):
 hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(*start),unreal.Vector(*end),
  unreal.TraceTypeQuery.ECC_VISIBILITY,False,ignored,unreal.DrawDebugTrace.NONE,True)
 if isinstance(hit,tuple):hit=next((v for v in hit if isinstance(v,unreal.HitResult)),None)
 return hit.to_dict() if hit is not None else None

def work():
 try:
  for tile in changed:
   if assets.does_asset_exist(tile['map']):raise RuntimeError('Preserving untracked existing level '+tile['map'])
   if not levels.new_level_from_template(tile['map'],tile['rockfall_parent_map']):raise RuntimeError('Clone failed')
   old_labels={str(a.get_actor_label()) for a in actors.get_all_level_actors()}
   record={'parent_map':tile['rockfall_parent_map'],'map':tile['map'],'new_meshes':[],
    'curb_collision_probes':[],'wire_no_collision_probes':[],'saved_complete':False}
   journal['tiles'][tile['id']]=record;targets={}
   for r in [r for r in s['records'] if r['tile']==tile['id']]:
    assert sha(r['source'])==r['sha256']
    mesh=unreal.LidarTerrainLibrary.create_circuit_mesh(r['source'],r['asset'],materials[r['kind']])
    if mesh is None:raise RuntimeError('Mesh creation failed '+r['id'])
    assets.save_loaded_asset(mesh)
    actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*r['location_cm']))
    component=actor.get_component_by_class(unreal.StaticMeshComponent);component.set_static_mesh(mesh)
    component.set_collision_profile_name('BlockAll')
    expected=unreal.CollisionEnabled.QUERY_AND_PHYSICS if r['collision_enabled'] else unreal.CollisionEnabled.NO_COLLISION
    component.set_collision_enabled(expected)
    if component.get_collision_enabled()!=expected:raise RuntimeError('Wrong new actor collision mode')
    actor.set_actor_label(r['id']);actor.set_editor_property('tags',['RockfallEdge'])
    targets[r['kind']]=actor
    record['new_meshes'].append({'id':r['id'],'vertices_expected':r['vertices'],'triangles_expected':r['triangles'],
      'component_collision_enabled':str(component.get_collision_enabled()),'asset':mesh.get_path_name()})
   record['parent_actor_labels_preserved']=old_labels.issubset({str(a.get_actor_label()) for a in actors.get_all_level_actors()})
   if not record['parent_actor_labels_preserved']:raise RuntimeError('Parent actor was removed')
   journal_path.write_text(json.dumps(journal,indent=2));yield
   components=[a.get_component_by_class(unreal.StaticMeshComponent) for a in actors.get_all_level_actors() if isinstance(a,unreal.StaticMeshActor)]
   states=[c.get_collision_enabled() for c in components]
   try:
    for c in components:c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    terrain=json.loads(unreal.LidarTerrainLibrary.verify_lidar_world_tile(tile['heightmap'],tile['holes']))
   finally:
    for c,state in zip(components,states):c.set_collision_enabled(state)
   record['native_height_readback']=terrain
   if not terrain['passed']:raise RuntimeError('Native Landscape changed')
   yield
   world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
   all_actors=list(actors.get_all_level_actors());curb=targets['rockfall_curb'];wire=targets['rockfall_net']
   for probe in s['curb_collision_probes']:
    hit=trace(world,probe['start_cm'],probe['end_cm'],[a for a in all_actors if a!=curb])
    passed=bool(hit and hit.get('blocking_hit') and hit.get('hit_actor')==curb)
    record['curb_collision_probes'].append({'passed':passed})
    if not passed:raise RuntimeError('Missing native curb collision')
   lines=s.get('net_wire_centerlines_cm') or [[q,q] for q in s['net_surface_centers_cm']];stride=max(1,len(lines)//64)
   for line in lines[::stride]:
    c=[(a+b)/2 for a,b in zip(*line)];start=[c[0],c[1],c[2]+50];end=[c[0],c[1],c[2]-50]
    hit=trace(world,start,end,[a for a in all_actors if a!=wire]);passed=not hit or not hit.get('blocking_hit')
    record['wire_no_collision_probes'].append({'passed':bool(passed)})
    if not passed:raise RuntimeError('Decorative draped net became a solid barrier')
   levels.save_current_level();record['saved_complete']=True
   journal_path.write_text(json.dumps(journal,indent=2));unreal.log('ROCKFALL_TILE_IMPORTED '+tile['id'])
  journal['protected_files_unchanged']=all(sha(p)==value for p,value in before.items())
  if not journal['protected_files_unchanged']:raise RuntimeError('Protected parent asset changed')
  journal['all_imported']=len(journal['tiles'])==len(changed) and all(t['saved_complete'] for t in journal['tiles'].values())
  journal['ended_unix']=time.time();journal_path.write_text(json.dumps(journal,indent=2))
  report={'build_id':build,'manifest':str(manifest_path),'all_imported':journal['all_imported'],
   'parent_import':str(parent/'import_report.json'),'rockfall_import':str(journal_path),'map':'/Game/Maps/CircuitoGuidabile',
   'activated':False,'root_map_modified':False,'parent_height_and_pavement_data_preserved':True,
   'native_curb_positive_probes':sum(len(t['curb_collision_probes']) for t in journal['tiles'].values()),
   'native_wire_no_collision_probes':sum(len(t['wire_no_collision_probes']) for t in journal['tiles'].values()),'visual_review_complete':False}
  (draft/'import_report.json').write_text(json.dumps(report,indent=2));unreal.log('ROCKFALL_EDGES_IMPORTED '+build)
 except BaseException as error:
  journal['error']=repr(error);journal['ended_unix']=time.time();journal['protected_files_unchanged']=all(sha(p)==value for p,value in before.items())
  journal_path.write_text(json.dumps(journal,indent=2));raise

generator=work();last_step=time.monotonic();advancing=False
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
def tick(_):
 global advancing,last_step
 if advancing or time.monotonic()-last_step<1:return
 advancing=True;last_step=time.monotonic()
 try:next(generator)
 except StopIteration:
  unreal.unregister_slate_post_tick_callback(handle);unreal.EditorPythonScripting.set_keep_python_script_alive(False)
 except BaseException:
  import traceback
  unreal.log_error(traceback.format_exc());unreal.unregister_slate_post_tick_callback(handle)
  unreal.EditorPythonScripting.set_keep_python_script_alive(False)
 finally:advancing=False
handle=unreal.register_slate_post_tick_callback(tick)
