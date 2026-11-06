"""Generate a native masked material and assign it only in cloned levels."""
import hashlib
import json
import math
import os
from pathlib import Path
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve().parent
manifest=Path(os.environ['SOFFUMBERGO_MATERIAL_MANIFEST']);m=json.loads(manifest.read_text())
variant=m['shoulder_material_variant'];build=m['build_id'];draft=ROOT/'results/road_drafts'/build
assets=unreal.EditorAssetLibrary;levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);lib=unreal.MaterialEditingLibrary


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


changed=[t for t in m['tiles'] if t.get('material_parent_map')]
protected=[ROOT/'parameters/current_road_design.json',ROOT/'Unreal/Content/Data/circuit_driving_world.json',
    ROOT/'Unreal/Content/Data/circuit_itinerary.json',ROOT/'Unreal/Content/Maps/CircuitoGuidabile.umap',
    ROOT/'Unreal/Content/World/Materials/M_Road_shoulder.uasset']
protected += [ROOT/'Unreal/Content'/(t['material_parent_map'].removeprefix('/Game/')+'.umap') for t in changed]
protected += [ROOT/'Unreal/Content'/(r['asset'].removeprefix('/Game/')+'.uasset') for r in m['meshes']]
before={str(p):sha(p) for p in protected};journal_path=draft/'material_native_import.json'
if journal_path.exists():raise RuntimeError('Preserve previous material import')
journal={'build_id':build,'protected_before':before,'tiles':{},'all_imported':False}
journal_path.write_text(json.dumps(journal,indent=2))
path=variant['material_asset']
if assets.does_asset_exist(path):raise RuntimeError('Preserving existing material')
folder,name=path.rsplit('/',1)
mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
mat.set_editor_property('two_sided',True);mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
mat.set_editor_property('opacity_mask_clip_value',variant['config']['opacity_clip'])
old=unreal.load_asset('/Game/World/Materials/M_Road_shoulder')
mat.set_editor_property('phys_material',old.get_editor_property('phys_material'))


def node(cls):return lib.create_material_expression(mat,cls)


def scalar(value):
    n=node(unreal.MaterialExpressionConstant);n.set_editor_property('r',value);return n


def vector(x,y,z):
    n=node(unreal.MaterialExpressionConstant3Vector);n.set_editor_property('constant',unreal.LinearColor(x,y,z,1));return n


def connect(source,target,pin=''):
    if not lib.connect_material_expressions(source,'',target,pin):
        raise RuntimeError('Material connection failed: '+str(target.get_class().get_name())+' '+pin+' actual='+str(lib.get_material_expression_input_names(target)))


def physical_state(actor,component):
    mesh=component.get_editor_property('static_mesh')
    return {'mesh':mesh.get_path_name() if mesh else None,
        'actor_transform':str(actor.get_actor_transform()),
        'relative_location':str(component.get_editor_property('relative_location')),
        'relative_rotation':str(component.get_editor_property('relative_rotation')),
        'relative_scale3d':str(component.get_editor_property('relative_scale3d')),
        'collision_enabled':str(component.get_collision_enabled()),
        'collision_profile':str(component.get_collision_profile_name()),
        'simulate_physics':component.is_simulating_physics()}


color=vector(.15,.12,.075);roughness=scalar(.98)
normal=node(unreal.MaterialExpressionVertexNormalWS);up=vector(0,0,1);dot=node(unreal.MaterialExpressionDotProduct)
connect(normal,dot,'A');connect(up,dot,'B')
lo=math.cos(math.radians(variant['config']['earth_zero_opacity_above_degrees']))
hi=math.cos(math.radians(variant['config']['earth_full_opacity_below_degrees']))
subtract=node(unreal.MaterialExpressionSubtract);divide=node(unreal.MaterialExpressionDivide);clamp=node(unreal.MaterialExpressionClamp)
connect(dot,subtract,'A');connect(scalar(lo),subtract,'B')
connect(subtract,divide,'A');connect(scalar(hi-lo),divide,'B')
connect(divide,clamp)
for expression,prop in [(color,unreal.MaterialProperty.MP_BASE_COLOR),
        (roughness,unreal.MaterialProperty.MP_ROUGHNESS),(clamp,unreal.MaterialProperty.MP_OPACITY_MASK)]:
    if not lib.connect_material_property(expression,'',prop):raise RuntimeError('Material output connection failed: '+str(prop))
lib.recompile_material(mat);assets.save_loaded_asset(mat)
journal['physical_material_preserved']=mat.get_editor_property('phys_material')==old.get_editor_property('phys_material')
if not journal['physical_material_preserved']:raise RuntimeError('Physical material changed')
for tile in changed:
    if assets.does_asset_exist(tile['map']):raise RuntimeError('Preserving existing variant map')
    if not levels.new_level_from_template(tile['map'],tile['material_parent_map']):raise RuntimeError('Failed map clone')
    assigned=[]
    states={}
    for actor in actors.get_all_level_actors():
        if actor.actor_has_tag('RoadShoulder'):
            component=actor.get_component_by_class(unreal.StaticMeshComponent)
            state=physical_state(actor,component)
            component.set_material(0,mat);assigned.append(actor.get_actor_label())
            if physical_state(actor,component)!=state:raise RuntimeError('Material assignment changed component physics')
            states[actor.get_actor_label()]=state
    if not assigned:raise RuntimeError('No earth overlay found in cloned map')
    if not levels.save_current_level():raise RuntimeError('Failed to save material variant map')
    journal['tiles'][tile['id']]={'map':tile['map'],'assigned':assigned,'saved_complete':True,
        'component_physical_state_before_and_after':states,'component_physics_preserved':True}
    journal_path.write_text(json.dumps(journal,indent=2))
    unreal.log('SHOULDER_MATERIAL_TILE '+tile['id'])
if not all(sha(p)==value for p,value in before.items()):raise RuntimeError('Protected parent changed')
journal.update(all_imported=len(journal['tiles'])==len(changed),protected_files_unchanged=True)
journal_path.write_text(json.dumps(journal,indent=2))
(draft/'import_report.json').write_text(json.dumps({'build_id':build,'manifest':str(manifest),
    'all_imported':journal['all_imported'],'journal':str(journal_path),'activated':False,
    'geometry_and_physics_changed':False,'diagnostic_only':not variant['full_territory_variant']},indent=2))
unreal.log('SHOULDER_MATERIAL_IMPORTED '+build)
