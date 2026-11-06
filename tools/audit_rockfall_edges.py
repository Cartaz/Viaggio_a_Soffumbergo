"""Independent preservation/clearance audit of a draped net and roadside curb."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import shapely
from prepare_reentry_checks import NativeGround
from road_surface import RoadSurface

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise RuntimeError('Preserve previous audit')
    m=json.loads(args.manifest.read_text());s=m['rockfall_edges'];old=json.loads(Path(s['parent_manifest']).read_text())
    before={r['id']:r for r in old['meshes']};after={r['id']:r for r in m['meshes']}
    tiles={t['id']:t for t in old['tiles']}
    checks={'every_parent_mesh_record_and_source_byte_preserved':all(after[k]==v and sha(v['source'])==v['sha256'] for k,v in before.items()),
      'only_explicit_new_meshes_added':set(after)-set(before)=={r['id'] for r in s['records']},
      'input_fingerprints_current':all(sha(f)==value for f,value in s['input_sha256'].items()),
      'height_and_hole_sources_unchanged':all(t['heightmap']==tiles[t['id']]['heightmap'] and t['holes']==tiles[t['id']]['holes'] and sha(t['heightmap'])==tiles[t['id']]['height_sha256'] and sha(t['holes'])==tiles[t['id']]['holes_sha256'] for t in m['tiles']),
      'source_reviews_no_metric_measurement_claim':s['metric_dimensions_measured'] is False,
      'uncertain_observed_ends_not_claimed':s['observed_real_world_ends_established'] is False}
    route_old=json.loads((Path(s['parent_draft'])/'circuit_itinerary.json').read_text())
    route_new=json.loads((ROOT/'results/road_drafts'/m['build_id']/'circuit_itinerary.json').read_text())
    for key in ['build_id','rockfall_parent_build_id','rockfall_variant_physically_verified']:
        route_old.pop(key,None);route_new.pop(key,None)
    checks['every_original_itinerary_field_preserved']=route_old==route_new
    world_old=json.loads((Path(s['parent_draft'])/'circuit_driving_world.json').read_text())
    world_new=json.loads((ROOT/'results/road_drafts'/m['build_id']/'circuit_driving_world.json').read_text())
    world_old.pop('build_id');world_new.pop('build_id')
    for a,b in zip(world_old['tiles'],world_new['tiles']):a.pop('map');b.pop('map')
    checks['all_non_map_world_fields_preserved']=world_old==world_new
    road=RoadSurface(old);ground=NativeGround(old);rows=[];minimum_clearance=float('inf');wire_gap=float('inf');curb_joint=0.
    for r in s['records']:
        data=json.loads(Path(r['source']).read_text());local=np.asarray(data['vertices_cm']);v=(local+np.asarray(r['location_cm']))/100
        tri=np.asarray(data['triangles'])
        if data.get('surface_net'):
            faces=v[tri];area=np.linalg.norm(np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0]),axis=1)/2
            samples=np.concatenate([v,faces.mean(1),(faces[:,0]+faces[:,1])/2,(faces[:,1]+faces[:,2])/2,(faces[:,2]+faces[:,0])/2])
            gap=samples[:,2]-ground.sample(samples[:,:2]);wire_gap=float(gap.min())
            checks['masked_net_native_triangle_skin_valid']=bool(np.isfinite(v).all() and area.min()>1.e-12)
            checks['masked_net_triangle_interiors_follow_native_ground']=bool(np.isfinite(gap).all() and np.max(np.abs(gap-s['config']['net_vertical_standoff_m']))<1.e-6)
            checks['net_has_no_physical_hulls_or_barrier_collision']='collision_convexes_cm' not in data and r['collision_enabled'] is False
            checks['wire_is_above_native_ground']=wire_gap>=s['config']['minimum_wire_ground_clearance_m']
            checks[r['id']+'_source_signature_matches']=sha(r['source'])==r['sha256']
            _,d=road.tree.query_nearest(shapely.polygons(faces[:,:,:2]*100),all_matches=False,return_distance=True)
            clearance=float(d.min()/100);minimum_clearance=min(minimum_clearance,clearance)
            rows.append({'id':r['id'],'vertices':len(v),'triangles':len(tri),'minimum_triangle_area_m2':float(area.min()),'minimum_asphalt_clearance_m':clearance,'representation':'Masked metric hex material on native triangles; no closed wire prism claim'})
            continue
        solids=v.reshape(-1,8,3);f=tri.reshape(-1,12,3)-np.arange(len(solids))[:,None,None]*8
        face=solids[np.arange(len(solids))[:,None,None],f];face-=solids.mean(1)[:,None,None,:]
        volumes=np.einsum('nfi,nfi->nf',face[:,:,0],np.cross(face[:,:,1],face[:,:,2])).sum(1)/6
        normals=np.cross(face[:,:,1]-face[:,:,0],face[:,:,2]-face[:,:,0])
        distance=np.einsum('nfvi,nfi->nfv',(solids-solids.mean(1)[:,None,:])[:,None,:,:]-face[:,:,0,None,:],normals)
        convex=bool((distance.max(2)<=1.e-7*np.linalg.norm(normals,axis=2)).all())
        # Full per-face incidence, rather than volume alone, proves closure.
        closed=True
        for ff in np.unique(f,axis=0):
            edges={}
            for a,b,c in ff:
                for x,y in [(a,b),(b,c),(c,a)]:edges[(min(x,y),max(x,y))]=edges.get((min(x,y),max(x,y)),0)+1
            closed=closed and all(n==2 for n in edges.values())
        checks[r['id']+'_valid_closed_outward_solids']=bool(np.isfinite(v).all() and volumes.min()>1.e-13 and convex and closed)
        checks[r['id']+'_source_signature_matches']=sha(r['source'])==r['sha256']
        _,d=road.tree.query_nearest(shapely.points(v[:,:2]*100),all_matches=False,return_distance=True)
        clearance=float(d.min()/100);minimum_clearance=min(minimum_clearance,clearance)
        if r['kind']=='rockfall_curb':
            checks['curb_render_equals_convex_collision']=np.array_equal(np.asarray(data['collision_convexes_cm']),local.reshape(-1,8,3)) and r['collision_enabled'] is True
            for joint in s['curb_shared_joints']:
                a=solids[joint['left_solid']][[1,2,5,6]];b=solids[joint['right_solid']][[0,3,4,7]]
                curb_joint=max(curb_joint,float(np.abs(np.array(sorted(map(tuple,a)))-np.array(sorted(map(tuple,b)))).max()))
            # Footprints must remain outside asphalt, including their faces.
            polygons=shapely.polygons(solids[:,:4,:2]*100)
            _,dd=road.tree.query_nearest(polygons,all_matches=False,return_distance=True)
            checks['entire_curb_footprint_clear_of_asphalt']=float(dd.min()/100)>=s['config']['minimum_asphalt_clearance_m']
        else:
            checks['net_has_no_physical_hulls_or_barrier_collision']='collision_convexes_cm' not in data and r['collision_enabled'] is False
            # Check actual saved tube corners and centreline interior samples.
            gap=v[:,2]-ground.sample(v[:,:2]);wire_gap=float(gap.min())
            line=np.asarray(s['net_wire_centerlines_cm'])/100
            for t in [.25,.5,.75]:
                q=line[:,0]*(1-t)+line[:,1]*t;wire_gap=min(wire_gap,float((q[:,2]-ground.sample(q[:,:2])).min()))
            checks['wire_is_above_native_ground']=bool(np.isfinite(wire_gap) and wire_gap>=s['config']['minimum_wire_ground_clearance_m']-.005)
        rows.append({'id':r['id'],'closed_solids':len(solids),'vertices':len(v),'triangles':len(tri),'minimum_volume_m3':float(volumes.min()),'minimum_vertex_asphalt_clearance_m':clearance})
    checks['all_new_vertices_clear_of_asphalt']=minimum_clearance>=s['config']['minimum_asphalt_clearance_m']
    checks['curb_shared_cross_sections_exact']=curb_joint<1.e-7
    report={'build_id':m['build_id'],'parent_build_id':s['parent_build_id'],'passed':all(checks.values()),'checks':checks,'new_meshes':rows,
      'minimum_asphalt_clearance_m':minimum_clearance,'minimum_wire_ground_clearance_m':wire_gap,'maximum_curb_joint_error_m':curb_joint,
      'scope':'Immutable data, saved geometry, no wire barrier collision and geometric clearance only; native import, driven tests, visual fidelity and performance are separate.'}
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False));print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
