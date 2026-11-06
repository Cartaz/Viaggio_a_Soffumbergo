"""Cheap geometric preflight before generating a full versioned road draft."""
import argparse
import json
from pathlib import Path
import numpy as np
from road_alignment import align_observed_benches

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
out=root/args.output
if out.exists():raise RuntimeError('Preserve previous preflight')
m=json.loads((root/'terrain/road_design/4a05593a4282/manifest.json').read_text())
origin=np.asarray(m['origin_ENH_m'])
mosaic=json.loads((root/'terrain/lidar_mosaic/manifest.json').read_text())
height=np.load(root/'terrain/lidar_mosaic/height_m.npy',mmap_mode='r')
def sample(x,y):
    xx=(x+origin[0]-mosaic['origin_E_N_m'][0])/mosaic['step_m']
    yy=(mosaic['origin_E_N_m'][1]-origin[1]+y)/mosaic['step_m']
    c=np.floor(xx).astype(int);r=np.floor(yy).astype(int);dx=xx-c;dy=yy-r
    return ((1-dy)*((1-dx)*height[r,c]+dx*height[r,c+1])+dy*((1-dx)*height[r+1,c]+dx*height[r+1,c+1]))-origin[2]
profile=np.asarray(m['profile_UE_cm'])[:,[0,2,1]]/100
config=json.loads((root/'parameters/road_bench_alignment.json').read_text())
adjusted,report=align_observed_benches(profile,profile[:-1].copy(),sample,config)
report['reference_world']=m['build_id']
report['world_modified']=False
out.write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
