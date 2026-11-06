"""Independently check imported-input solids against actual asphalt and parent data."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import shapely
from prepare_reentry_checks import NativeGround
from road_surface import RoadSurface

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise RuntimeError('Preserve earlier audit')
    m=json.loads(args.manifest.read_text());s=m['roadside_structures']
    parent=json.loads(Path(s['parent_manifest']).read_text())
    old_mesh={r['id']:r for r in parent['meshes']};new_mesh={r['id']:r for r in m['meshes']}
    replaced=set(s.get('replaced_mesh_ids',[]))
    expected_replaced={r['id'] for r in parent.get('roadside_structures',{}).get('records',[])}
    preserved_meshes=all(new_mesh[name]==record and sha(record['source'])==record['sha256'] for name,record in old_mesh.items() if name not in replaced)
    old_tiles={t['id']:t for t in parent['tiles']}
    height_bytes=all(t['heightmap']==old_tiles[t['id']]['heightmap'] and t['holes']==old_tiles[t['id']]['holes']
                     and sha(t['heightmap'])==old_tiles[t['id']]['height_sha256']
                     and sha(t['holes'])==old_tiles[t['id']]['holes_sha256'] for t in m['tiles'])
    parent_route=json.loads((Path(s['parent_draft'])/'circuit_itinerary.json').read_text())
    new_route=json.loads((ROOT/'results/road_drafts'/m['build_id']/'circuit_itinerary.json').read_text())
    for key in ['build_id','structure_parent_build_id','structure_variant_physically_verified']:
        parent_route.pop(key,None);new_route.pop(key,None)
    route_unchanged=parent_route==new_route
    road=RoadSurface(parent);ground=NativeGround(parent)
    polygons=[];post_ends=[];post_bases=[];rows=[];volumes=[];vertices_by_id={};convex_ok=True
    for mesh in s['records']:
        data=json.loads(Path(mesh['source']).read_text())
        v=(np.asarray(data['vertices_cm'])+np.asarray(mesh['location_cm']))/100
        vertices_by_id[mesh['id']]=v
        tri=np.asarray(data['triangles'])
        if len(v)%8 or len(tri)%12:raise RuntimeError('Unexpected non-prismatic structure topology')
        if not np.isfinite(v).all():raise RuntimeError('Non-finite structure')
        solids=v.reshape(-1,8,3)
        if 'collision_convexes_cm' in data:
            convex=np.asarray(data['collision_convexes_cm'])
            if not np.array_equal(convex,np.asarray(data['vertices_cm']).reshape(-1,8,3)):
                raise RuntimeError('Convex collision differs from rendered solid geometry')
        for i,solid in enumerate(solids):
            polygons.append(shapely.Polygon(solid[:4,:2]));faces=solid[np.asarray(data['triangles'])[i*12:i*12+12]-8*i]
            # Translate before the divergence integral to avoid cancellation at
            # large geographic coordinates. Every solid must enclose volume.
            faces=faces-solid.mean(axis=0)
            normals=np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0])
            signed=np.einsum('fvi,fi->fv',(solid-solid.mean(axis=0))[None,:,:]-faces[:,0,None,:],normals)
            convex_ok=convex_ok and bool((signed.max(axis=1)<=1.e-7*np.linalg.norm(normals,axis=1)).all())
            volume=np.einsum('ij,ij->i',faces[:,0],np.cross(faces[:,1],faces[:,2])).sum()/6
            volumes.append(float(volume))
            edge=np.linalg.norm(solid[1,:2]-solid[0,:2])
            is_post=mesh['kind']=='metal' and abs(edge-s['config']['guardrail_post_width_m'])<1.e-5
            if is_post:
                post_ends.append(solid[:4,:2].mean(axis=0));post_bases.append(float(solid[:4,2].max()))
        rows.append({'mesh_id':mesh['id'],'kind':mesh['kind'],'solid_count':len(solids),
                     'source_signature_matches':sha(mesh['source'])==mesh['sha256']})
    # RoadSurface polygons are in centimetres, whereas solid footprints are in
    # metres. Query a correctly scaled independent copy of every solid.
    scaled=shapely.transform(np.asarray(polygons,dtype=object),lambda q:q*100)
    _,distance=road.tree.query_nearest(scaled,all_matches=False,return_distance=True)
    min_clearance=float(distance.min()/100)
    post_gap=np.asarray(post_bases)-ground.sample(np.asarray(post_ends))
    joint_errors=[]
    for joint in s.get('shared_cross_section_joints',[]):
        ends=[vertices_by_id[e['mesh_id']][e['vertex_indices']] for e in joint['ends']]
        # Compare unordered rectangles, independently of end-face winding.
        reference=np.asarray(sorted(map(tuple,ends[0])))
        joint_errors.extend(float(np.abs(np.asarray(sorted(map(tuple,end)))-reference).max()) for end in ends[1:])
    checks={'parent_mesh_records_and_bytes_preserved':preserved_meshes,'native_height_and_hole_bytes_preserved':height_bytes,
            'all_original_itinerary_fields_unchanged':route_unchanged,
            'all_structure_signatures_match':all(r['source_signature_matches'] for r in rows),
            'positive_closed_solid_volumes':min(volumes)>1.e-8,
            'rendered_solids_are_exact_convex_collision_hulls':convex_ok,
            'replacement_scope_explicit':replaced==expected_replaced,
            'asphalt_clearance':min_clearance>=s['config']['minimum_asphalt_clearance_m']-1.e-7,
            'all_posts_embed_in_native_ground':bool(np.isfinite(post_gap).all() and post_gap.max()<=-.15)}
    if s['config'].get('continuous_joints'):
        checks['shared_cross_sections_match_without_gaps']=bool(joint_errors) and max(joint_errors)<1.e-7
        checks['no_discarded_structural_segments']=not s['discarded_intruding_solids']
    observed_controls=[c for c in s['config']['controls'] if c.get('guardrail_extent')]
    if observed_controls:
        expected_terminals=sum(sum(c['guardrail_extent'].get(k) is not None for k in ['minimum_forward_m','maximum_forward_m']) for c in observed_controls)
        checks['explicit_observed_terminals_built']=len(s.get('observed_terminals',[]))==expected_terminals and all(t['convex_loft_solids']>0 for t in s.get('observed_terminals',[]))
        checks['observed_open_approach_has_native_absence_probes']=bool(s.get('open_collision_probes')) and bool(s.get('observed_open_intervals_omitted'))
        checks['every_observed_control_has_absence_probes']=all(any(p['control']==c['id'] for p in s.get('open_collision_probes',[])) for c in observed_controls)
    report={'passed':all(checks.values()),'build_id':m['build_id'],'parent_build_id':s['parent_build_id'],
        'checks':checks,'minimum_asphalt_clearance_m':min_clearance,'max_post_base_above_native_ground_m':float(post_gap.max()),
        'solids':len(polygons),'posts':len(post_ends),'minimum_solid_volume_m3':min(volumes),'meshes':rows,
        'shared_joints':len(s.get('shared_cross_section_joints',[])),
        'maximum_shared_cross_section_error_m':max(joint_errors,default=0),
        'scope':'Geometry and immutable-data audit only; native collision, driven lap and visual review are separate requirements.'}
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False));print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
