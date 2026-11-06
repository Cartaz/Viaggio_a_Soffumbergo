"""Inventory every major changed native sample, joining regions across tile seams.

This is a diagnostic of engineered cut/fill, not a survey of retaining walls.
Original and derived R16 files are read only. No world data is activated.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from pyproj import Transformer
from road_surface import RoadSurface

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--threshold-m',type=float,default=1.5)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not np.isfinite(args.threshold_m) or args.threshold_m<=0:raise ValueError('Positive threshold required')
    output=args.output.resolve()
    if output.exists() or output.with_suffix('.npz').exists():raise RuntimeError('Preserve earlier inventory')
    manifest=json.loads(args.manifest.read_text())
    base_path=ROOT/'terrain/world_tiles/manifest.json'
    base=json.loads(base_path.read_text());raw_by_id={t['id']:t for t in base['tiles']}
    quant=base['height_quantization_m'];origin=np.asarray(manifest['origin_ENH_m'])
    zero=base['source_height_bounds_m'][0]-origin[2]
    cells={};fingerprints={str(args.manifest.resolve()):sha(args.manifest),str(base_path):sha(base_path)}
    duplicates=0;excluded_hidden=0;changed_below=0;step=None
    for tile in manifest['tiles']:
        raw=raw_by_id[tile['id']]
        if tile['heightmap']==raw['heightmap']:continue
        n=tile['samples'];current_step=tile['xy_scale_cm']/100
        if step is not None and abs(current_step-step)>1.e-9:raise ValueError('Inconsistent grid')
        step=current_step
        arrays=[]
        for path,dtype in [(raw['heightmap'],'<u2'),(tile['heightmap'],'<u2'),(raw['holes'],'u1'),(tile['holes'],'u1')]:
            fingerprints[str(path)]=sha(path)
            arrays.append(np.fromfile(path,dtype).reshape(n,n))
        old,new,old_holes,new_holes=arrays
        delta=(new.astype(float)-old.astype(float))*quant
        major=np.abs(delta)>=args.threshold_m
        valid=(old_holes==0)&(new_holes==0)
        excluded_hidden+=int(np.count_nonzero(major&~valid))
        changed_below+=int(np.count_nonzero(valid&(delta!=0)&~major))
        iy,ix=np.nonzero(major&valid)
        x0,y0=np.asarray(tile['bounds_xy_cm'][:2])/100
        for r,c in zip(iy,ix):
            x=x0+c*step;y=y0+r*step
            key=(int(round(x/step)),int(round(y/step)))
            value=(float(old[r,c])*quant+zero,float(new[r,c])*quant+zero)
            if key in cells:
                duplicates+=1
                if not np.allclose(cells[key],value,atol=1.e-8,rtol=0):raise ValueError('Shared grid samples disagree')
            else:cells[key]=value
    keys=list(cells);xy=np.asarray(keys,dtype=float)*step
    heights=np.asarray([cells[k] for k in keys]);delta=heights[:,1]-heights[:,0]
    positions={key:i for i,key in enumerate(keys)}
    # Eight-neighbour components are joined in the global grid, with cut and
    # fill kept separate. Shared tile borders do not split one physical region.
    seen=set();components=[]
    for start in range(len(keys)):
        if start in seen:continue
        fill=delta[start]>0;stack=[start];seen.add(start);ids=[]
        while stack:
            i=stack.pop();ids.append(i);x,y=keys[i]
            for dx in [-1,0,1]:
                for dy in [-1,0,1]:
                    if dx==dy==0:continue
                    j=positions.get((x+dx,y+dy))
                    if j is not None and j not in seen and (delta[j]>0)==fill:
                        seen.add(j);stack.append(j)
        components.append(np.asarray(ids))
    road=RoadSurface(manifest);road_z,road_distance=road.sample(xy*100)
    geographic=Transformer.from_crs(6708,4326,always_xy=True)
    regions=[]
    for ids in components:
        peak=ids[np.argmax(np.abs(delta[ids]))]
        longitude,latitude=geographic.transform(xy[peak,0]+origin[0],origin[1]-xy[peak,1])
        regions.append({'kind':'fill' if delta[peak]>0 else 'cut','sample_count':len(ids),
            'peak_delta_m':float(delta[peak]),'peak_UE_xy_m':xy[peak].tolist(),
            'peak_source_local_height_m':float(heights[peak,0]),'peak_derived_local_height_m':float(heights[peak,1]),
            'peak_asphalt_distance_m':float(road_distance[peak]/100),
            'peak_latitude':latitude,'peak_longitude':longitude,
            'bounds_UE_xy_m':[*xy[ids].min(axis=0).tolist(),*xy[ids].max(axis=0).tolist()],
            'samples_under_asphalt':int(np.count_nonzero(road_distance[ids]<.01)),
            'review_status':'Open: classify observed support/bank and inspect game geometry; no automatic acceptance.'})
    regions.sort(key=lambda r:abs(r['peak_delta_m']),reverse=True)
    if sum(r['sample_count'] for r in regions)!=len(keys):raise RuntimeError('Incomplete inventory coverage')
    output.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(output.with_suffix('.npz'),xy_m=xy,source_derived_height_m=heights,
                        asphalt_height_m=road_z/100,asphalt_distance_m=road_distance/100)
    report={'build_id':manifest['build_id'],'threshold_m':args.threshold_m,'native_step_m':step,
            'scope':'Every visible native grid sample with encoded derived-minus-source height at or above the threshold; not a continuous triangle maximum or a metric wall survey.',
            'major_samples_unique':len(keys),'deduplicated_seam_samples':duplicates,
            'hidden_samples_excluded_with_tile_duplicates':excluded_hidden,
            'smaller_changed_samples_with_tile_duplicates':changed_below,
            'region_count':len(regions),'regions':regions,'input_sha256':fingerprints,
            'world_modified':False,'all_structural_reviews_complete':False,
            'samples_archive':str(output.with_suffix('.npz'))}
    output.write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps({'build_id':manifest['build_id'],'major_samples':len(keys),'regions':len(regions),
                      'largest':regions[:5]},indent=2))


if __name__=='__main__':main()
