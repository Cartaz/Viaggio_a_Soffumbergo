"""Independent native-surface/immutability audit of replacement shoulders."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import shapely
from prepare_reentry_checks import NativeGround
from road_surface import RoadSurface


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise RuntimeError('Preserve earlier audit')
    m=json.loads(args.manifest.read_text());repair=m['shoulder_repair']
    parent=json.loads(Path(repair['parent_manifest']).read_text());ground=NativeGround(parent);road=RoadSurface(parent)
    old={r['id']:r for r in parent['meshes']};now={r['id']:r for r in m['meshes']}
    preserved=all(now[k]==r and sha(r['source'])==r['sha256'] for k,r in old.items() if r['kind']!='shoulder')
    native_bytes=all(t['heightmap']==p['heightmap'] and t['holes']==p['holes'] and
        sha(t['heightmap'])==p['height_sha256'] and sha(t['holes'])==p['holes_sha256'] for t,p in zip(m['tiles'],parent['tiles']))
    draft=args.output.parent;route=json.loads((draft/'circuit_itinerary.json').read_text())
    previous_route=json.loads((Path(repair['parent_draft'])/'circuit_itinerary.json').read_text())
    route.pop('build_id');previous_route.pop('build_id')
    rows=[];sample_count=0;boundary={}
    for info in repair['records']:
        data=json.loads(Path(info['source']).read_text());v=(np.asarray(data['vertices_cm'])+info['location_cm'])/100
        tri=np.asarray(data['triangles']);f=v[tri];distance=road.sample(v[:,:2]*100,clamp_to_triangle=True)[1]/100
        away=(distance[tri].min(axis=1)>=.15001)
        probes=np.einsum('ij,kjl->kil',np.array([[1/3,1/3,1/3],[.6,.2,.2],[.2,.6,.2],[.2,.2,.6]]),f[away]).reshape(-1,3)
        native=ground.sample(probes[:,:2]);error=probes[:,2]-native-.02
        sample_count+=len(probes)
        polygons=shapely.polygons(f[:,:,:2]);area=float(shapely.area(polygons).sum())
        source=json.loads(Path(old[info['id']]['source']).read_text())
        ov=(np.asarray(source['vertices_cm'])+old[info['id']]['location_cm'])/100
        footprint=shapely.union_all(shapely.polygons(ov[np.asarray(source['triangles']),:2]))
        tile=next(t for t in m['tiles'] if t['id']==info['tile'])
        x0,y0,x1,y1=np.asarray(tile['bounds_xy_cm'])/100;step=tile['xy_scale_cm']/100
        holes=np.fromfile(tile['holes'],'u1').reshape(tile['samples'],tile['samples'])
        masked=(holes[:-1,:-1]!=0)|(holes[1:,:-1]!=0)|(holes[:-1,1:]!=0)|(holes[1:,1:]!=0)
        yy,xx=np.nonzero(masked);cx=x0+(xx+.5)*step;cy=y0+(yy+.5)*step
        near=shapely.contains_xy(footprint.buffer(step/np.sqrt(2)+1.e-6),cx,cy)
        masks=shapely.box(cx[near]-step/2,cy[near]-step/2,cx[near]+step/2,cy[near]+step/2)
        expected=footprint.difference(shapely.union_all(masks))
        planar_error=abs(area-float(expected.area))
        shape_error=float(shapely.symmetric_difference(shapely.union_all(polygons),expected).area)
        max_error=float(np.abs(error).max()) if len(error) else 0
        center=f.mean(axis=1);gap=center[:,2]-ground.sample(center[:,:2])
        projected_cross=np.cross(f[:,1]-f[:,0],f[:,2]-f[:,0])[:,2]
        full_cross=np.cross(f[:,1]-f[:,0],f[:,2]-f[:,0]);native_precision=bool(((full_cross*full_cross).sum(axis=1)*1.e8>=1.e-8*(1-1.e-5)).all())
        for point in v[(np.abs(v[:,0]-x0)<1.e-6)|(np.abs(v[:,0]-x1)<1.e-6)|(np.abs(v[:,1]-y0)<1.e-6)|(np.abs(v[:,1]-y1)<1.e-6)]:
            boundary.setdefault(tuple(np.round(point[:2],6)),[]).append(float(point[2]))
        rows.append({'mesh_id':info['id'],'native_conformance_probe_count':len(probes),
            'native_conformance_max_error_m':max_error,'centroid_max_above_native_m':float(np.nanmax(gap)),
            'planar_footprint_area_error_m2':planar_error,'source_signature_matches':sha(info['source'])==info['sha256'],
            'planar_symmetric_difference_m2':shape_error,
            'parent_overlay_area_on_masked_native_cells_omitted_m2':float(footprint.area-expected.area),
            'finite':bool(np.isfinite(v).all() and np.isfinite(error).all()),
            'upward_noncollapsed_faces':bool((projected_cross>1.e-12).all()),
            'native_creator_precision':native_precision,
            'passed':bool(np.isfinite(error).all() and max_error<5.e-5 and planar_error<.001 and shape_error<.001 and (projected_cross>1.e-12).all() and native_precision)})
        print('OVERLAY_AUDIT '+info['tile']+' '+str(rows[-1]['passed']),flush=True)
    shared=[v for v in boundary.values() if len(v)>1];seam=max((max(v)-min(v) for v in shared),default=0)
    checks={'asphalt_bridges_and_anthropic_mesh_records_and_bytes_preserved':preserved,
        'native_heights_and_holes_preserved':native_bytes,'original_itinerary_preserved':route==previous_route,
        'all_overlay_sources_match':all(r['source_signature_matches'] for r in rows),
        'overlays_conform_to_native_triangles_away_from_seam':all(r['passed'] for r in rows),
        'shared_tile_vertex_heights_match':seam<1.e-7}
    report={'build_id':m['build_id'],'parent_build_id':parent['build_id'],'passed':all(checks.values()),'checks':checks,
        'native_conformance_probes':sample_count,'shared_shoulder_coordinates':len(shared),'max_shared_height_spread_m':seam,
        'meshes':rows,'scope':'Overlay geometry and source preservation only. The asphalt seam deliberately joins the road to native terrain. Native import, physics and visual checks remain required.'}
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False));print(json.dumps({k:v for k,v in report.items() if k!='meshes'},indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
