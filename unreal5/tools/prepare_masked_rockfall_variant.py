"""Native-triangle net skin with a metric world-projected hex mask.

The rejected wire candidate supplies the reviewed coverage. This derivative
starts from the same immutable parent, never from the visually rejected map.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
import shapely
from prepare_reentry_checks import NativeGround
from roadside_joints import joined_prism,convex_faces
from road_surface import RoadSurface
from prepare_roadside_structures import boundary_point

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--parent-draft',type=Path,required=True)
 p.add_argument('--wire-draft',type=Path,required=True);p.add_argument('--config',type=Path,required=True);args=p.parse_args()
 parent=args.parent_draft.resolve();original_path=Path(json.loads((parent/'import_report.json').read_text())['manifest'])
 old=json.loads(original_path.read_text());wire_path=Path(json.loads((args.wire_draft/'structure_preparation.json').read_text())['manifest'])
 template=json.loads(wire_path.read_text());s=template['rockfall_edges'];assert s['parent_build_id']==old['build_id']
 config=json.loads(args.config.read_text());assert config['net_representation']=='world_projected_hex_mask'
 inputs=[original_path,wire_path,args.config,parent/'circuit_driving_world.json',parent/'circuit_itinerary.json',Path(__file__),
  ROOT/'tools/import_rockfall_edges.py',ROOT/'tools/audit_rockfall_edges.py',ROOT/'tools/prepare_reentry_checks.py',
  ROOT/'tools/roadside_joints.py',ROOT/'tools/road_surface.py',ROOT/'tools/prepare_roadside_structures.py',
  ROOT/'Unreal/Source/SoffumbergoTerrainEditor/CircuitMesh.cpp']+[ROOT/f for f in config['source_reviews']]
 fingerprints={str(f.resolve()):sha(f) for f in inputs};build=hashlib.sha256(json.dumps(fingerprints,sort_keys=True).encode()).hexdigest()[:12]
 folder=ROOT/'terrain/rockfall_edges'/build;draft=ROOT/'results/road_drafts'/build
 if folder.exists() or draft.exists():raise RuntimeError('Preserve previous candidate')
 folder.mkdir(parents=True);draft.mkdir(parents=True)
 ground=NativeGround(old);sections=s['net_bank_sections'];station=np.asarray(sections['station_m'])
 edges=np.asarray(sections['asphalt_edge_UE_xy_m']);normals=np.asarray(sections['uphill_UE_xy_unit'])
 offsets=np.arange(config['net_start_offset_m'],config['bank_scan_width_m']+.00001,.1)
 xy=edges[:,None,:]+normals[:,None,:]*offsets[None,:,None]
 z=ground.sample(xy.reshape(-1,2)).reshape(len(station),-1)
 arc=np.c_[np.zeros(len(station)),np.cumsum(np.sqrt(np.diff(z,axis=1)**2+.1**2),axis=1)]
 reach=np.array([np.interp(config['net_surface_height_m'],a,offsets) for a in arc])
 lower=edges+normals*config['net_start_offset_m'];upper=edges+normals*reach[:,None]
 # Adjacent bank transects can overlap in plan at a tight bend. Form their
 # union explicitly, so there is one skin rather than overlapping sheets or
 # an invalid ribbon boundary. Native terrain triangles remain the surface.
 strips=[shapely.make_valid(shapely.Polygon([lower[i],lower[i+1],upper[i+1],upper[i]])) for i in range(len(lower)-1)]
 footprint=shapely.union_all(strips)
 if not footprint.is_valid:raise ValueError('Net coverage union is invalid')
 tile=next(t for t in old['tiles'] if t['id']==s['records'][0]['tile']);step=tile['xy_scale_cm']/100
 x0,y0,x1,y1=np.array(tile['bounds_xy_cm'])/100
 a,b,c,d=footprint.bounds
 faces=[]
 for i in range(max(0,int((a-x0)//step)),min(tile['samples']-1,int((c-x0)//step)+1)):
  for j in range(max(0,int((b-y0)//step)),min(tile['samples']-1,int((d-y0)//step)+1)):
   q=np.array([[x0+i*step,y0+j*step],[x0+(i+1)*step,y0+j*step],
               [x0+(i+1)*step,y0+(j+1)*step],[x0+i*step,y0+(j+1)*step]])
   for tri in [q[[0,1,2]],q[[0,2,3]]]:
    clipped=shapely.Polygon(tri).intersection(footprint)
    if clipped.is_empty or clipped.area<1.e-12:continue
    for part in shapely.get_parts(clipped):
     if part.geom_type!='Polygon':continue
     for t in shapely.get_parts(shapely.constrained_delaunay_triangles(part)):
      tt=np.asarray(t.exterior.coords)[:3]
      zz=ground.sample(tt)+config['net_vertical_standoff_m']
      if not np.isfinite(zz).all():raise ValueError('Net crosses missing native ground')
      vv=np.c_[tt,zz]
      if np.cross(vv[1]-vv[0],vv[2]-vv[0])[2]<0:vv=vv[[0,2,1]]
      faces.append(vv)
 vertices=np.asarray(faces).reshape(-1,3);triangles=np.arange(len(vertices)).reshape(-1,3)
 # Constant road-relative world axes keep the hex size independent of the
 # corrugated cut's local height derivatives. They do not alter the terrain.
 axis=edges[-1]-edges[0];axis/=np.linalg.norm(axis)
 across=np.array([-axis[1],axis[0]])
 if across@normals.mean(0)<0:across*=-1
 materials={'net_world_along_xy_unit':axis.tolist(),'net_world_uphill_xy_unit':across.tolist(),
  'net_projection_uphill_weight':config.get('net_projection_uphill_weight',.5),'net_mask_cell_radius_m':config['hex_circumradius_m'],
  'net_mask_wire_diameter_m':config['wire_diameter_m'],'net_mask_clip':.333}
 clo,chi=s['curb_profile_station_range_m'];ss=np.linspace(clo,chi,int(np.ceil((chi-clo)/config['section_step_m']))+1)
 curb_sections=[];road=RoadSurface(old)
 road_ids=road.tree.query(shapely.box(*(edges.min(0)*100-1500),*(edges.max(0)*100+1500)),predicate='intersects')
 road_footprint=shapely.transform(shapely.union_all(road.polygons[road_ids]),lambda p:p/100)
 profile=np.asarray(old['profile_UE_cm'])/100;profile_station=np.asarray(old['profile_station_m'])
 for pos in ss:
  n=np.array([np.interp(pos,station,normals[:,k]) for k in range(2)]);n/=np.linalg.norm(n)
  road_center=np.array([np.interp(pos,profile_station,profile[:,k]) for k in range(2)])
  edge=boundary_point(road_center,n,road_footprint)
  center=edge+n*config['curb_center_offset_m']
  # Read the exact asphalt boundary; no bank crest drives the curb top.
  road_z,dist=road.sample(edge*100);assert dist[0]<.01
  rz=float(road_z[0]/100);gz=float(ground.sample(center)[0])
  curb_sections.append({'center':center,'normal':n,'bottom':min(rz,gz)-config['curb_embed_m'],'top':rz+config['curb_exposure_m']})
 curbs=np.array([joined_prism([a,b],config['curb_width_m']) for a,b in zip(curb_sections,curb_sections[1:])])
 records=[];probes=[];location=np.array([*tile['location_cm'][:2],0])
 for kind,v,tri,collision in [('rockfall_net',vertices,triangles,False),('rockfall_curb',curbs.reshape(-1,3),np.concatenate([convex_faces(q)+i*8 for i,q in enumerate(curbs)]),True)]:
  local=np.round(v*100-location,6);name=kind+'_'+tile['id'];payload={'vertices_cm':local.tolist(),'triangles':tri.tolist()}
  if collision:payload['collision_convexes_cm']=local.reshape(-1,8,3).tolist();payload['closed_surface']=True
  else:payload['surface_net']=True
  f=folder/(name+'.json');f.write_text(json.dumps(payload,separators=(',',':')))
  records.append({'id':name,'tile':tile['id'],'kind':kind,'source':str(f),'sha256':sha(f),
   'asset':'/Game/World/Driving/F_'+build+'/Meshes/'+name,'location_cm':location.tolist(),'vertices':len(v),'triangles':len(tri),
   'collision_enabled':collision,'actor_tag':'RockfallEdge'})
 for q in curbs:
  center=q.mean(0);side=q[3,:2]-q[0,:2];side/=np.linalg.norm(side)
  probes.append({'start_cm':((center+np.r_[side*.5,0])*100).tolist(),'end_cm':((center-np.r_[side*.5,0])*100).tolist()})
 m=copy.deepcopy(old);m['build_id']=build;m['meshes']+=records
 for t in m['tiles']:
  t.pop('structure_parent_map',None)
  if t['id']==tile['id']:t['rockfall_parent_map']=t['map'];t['map']='/Game/World/Driving/F_'+build+'/Terrain/'+t['id']
 ns=copy.deepcopy(s);ns.update({'parent_build_id':old['build_id'],'parent_manifest':str(original_path),'parent_draft':str(parent),
  'input_sha256':fingerprints,'config':config,'records':records,'net_material_parameters':materials,
  'rejected_wire_coverage_reference':str(wire_path),'net_surface_triangle_count':len(faces),
  'net_surface_centers_cm':(np.asarray(faces).mean(1)*100).tolist(),'curb_collision_probes':probes})
 for key in ['net_wire_centerlines_cm','net_parametric_edges_m','net_hex_edges','net_wire_pieces']:ns.pop(key,None)
 m['rockfall_edges']=ns;m['report']={**m['report'],'build_id':build,'native_imported':False,'full_lap_driven':False}
 (folder/'manifest.json').write_text(json.dumps(m,indent=2))
 world=json.loads((parent/'circuit_driving_world.json').read_text());world['build_id']=build;maps={t['id']:t['map'] for t in m['tiles']}
 for t in world['tiles']:t['map']=maps[t['id']]
 route=json.loads((parent/'circuit_itinerary.json').read_text());route.update({'build_id':build,'rockfall_parent_build_id':old['build_id'],'rockfall_variant_physically_verified':False})
 (draft/'circuit_driving_world.json').write_text(json.dumps(world));(draft/'circuit_itinerary.json').write_text(json.dumps(route))
 report={'build_id':build,'parent_build_id':old['build_id'],'manifest':str(folder/'manifest.json'),'draft':str(draft),'activated':False,
  'added_mesh_count':2,'net_representation':config['net_representation'],'net_triangles':len(faces),'curb_solids':len(curbs),
  'net_profile_length_m':station[-1]-station[0],'curb_profile_length_m':chi-clo,'asphalt_and_terrain_preserved':True}
 (draft/'structure_preparation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
