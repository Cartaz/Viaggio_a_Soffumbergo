"""Locate remaining cut/fill against source Landscape without changing the world.

Cross sections are geometric diagnostics, not surveyed pavement widths or a
claim that the source DTM identifies retaining structures.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from pyproj import Transformer
from prepare_reentry_checks import NativeGround
from road_surface import RoadSurface

ROOT=Path(__file__).resolve().parents[1]


def finite_list(values):
    return [float(v) if np.isfinite(v) else None for v in values]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='results/grading_review_4a05593a4282_v1.json')
    parser.add_argument('--manifest',type=Path)
    args=parser.parse_args();output=ROOT/args.output
    if output.exists():raise RuntimeError('Preserve previous audit; use a new output')
    pointer=json.loads((ROOT/'parameters/current_road_design.json').read_text())
    m=json.loads((args.manifest or Path(pointer['manifest'])).read_text())
    base=json.loads((ROOT/'terrain/world_tiles/manifest.json').read_text())
    current=NativeGround(m);source=NativeGround(base)
    road=RoadSurface(m)
    axis=np.asarray(m['profile_UE_cm'])/100
    to_geo=Transformer.from_crs(6708,4326,always_xy=True)
    rows=[]
    for earth in sorted(m['earthworks'],key=lambda e:e['max_grading_delta_m'],reverse=True):
        peak=np.asarray(earth['peak_change_UE_m'])
        i=int(np.argmin(np.linalg.norm(axis[:,:2]-peak[:2],axis=1)))
        center=axis[i,:2]
        tangent=axis[min(i+2,len(axis)-1),:2]-axis[max(0,i-2),:2]
        tangent/=np.linalg.norm(tangent);normal=np.array([-tangent[1],tangent[0]])
        offsets=np.arange(-8,8.001,.25)
        xy=center+offsets[:,None]*normal
        raw=source.sample(xy);now=current.sample(xy)
        road_z,distance=road.sample(xy*100)
        lo,la=to_geo.transform(center[0]+m['origin_ENH_m'][0],m['origin_ENH_m'][1]-center[1])
        peak_z,peak_dist=road.sample(peak[:2]*100)
        delta=now-raw
        rows.append({'tile':earth['id'],'max_tile_grading_m':earth['max_grading_delta_m'],
                     'peak_UE_m':peak.tolist(),'peak_asphalt_distance_m':float(peak_dist[0]/100),
                     'nearest_axis_index':i,'nearest_axis_UE_m':axis[i].tolist(),
                     'axis_latitude':la,'axis_longitude':lo,
                     'source_at_axis_m':float(source.sample(center)[0]),
                     'road_minus_source_at_axis_m':float(axis[i,2]-source.sample(center)[0]),
                     'normal_UE_xy':normal.tolist(),'offset_m':offsets.tolist(),
                     'source_height_local_m':finite_list(raw),'current_height_local_m':finite_list(now),
                     'road_height_local_m':[float(z/100) if d<.001 else None for z,d in zip(road_z,distance)],
                     'sampled_cross_section_grading_m':finite_list(delta),
                     'absent_or_masked_current_samples':int(np.count_nonzero(~np.isfinite(now))),
                     'review_status':'Open: compare source bench, alignment and observed banks/structures before accepting major grading.'})
    report={'build_id':m['build_id'],'world_modified':False,
            'height_quantization_m':base['height_quantization_m'],
            'scope':'One cross section through the route nearest each tile peak; peaks are not a complete spatial inventory of cut/fill.',
            'all_major_grading_accepted':False,'sections':rows}
    output.write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps({'output':str(output),'top_sections':[{k:r[k] for k in ['tile','peak_asphalt_distance_m','road_minus_source_at_axis_m','axis_latitude','axis_longitude']} for r in rows[:8]]},indent=2))


if __name__=='__main__':main()
