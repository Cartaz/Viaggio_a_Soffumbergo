"""CPU-only coverage/quantization audit from raw mosaic to original native tiles."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise RuntimeError('Preserve previous coverage audit')
    raw_path=ROOT/'terrain/lidar_mosaic/manifest.json';native_path=ROOT/'terrain/world_tiles/manifest.json'
    raw=json.loads(raw_path.read_text());native=json.loads(native_path.read_text())
    height=np.load(raw_path.parent/'height_m.npy',mmap_mode='r');owners=np.load(raw_path.parent/'source_index.npy',mmap_mode='r')
    assert height.shape==owners.shape==(raw['height'],raw['width'])
    covered=np.zeros(height.shape,bool);max_error=0.;native_valid_sum=0;outside_valid=0;invented=0
    coordinate_errors=[];files={}
    for tile in native['tiles']:
        hpath=Path(tile['heightmap']);mpath=Path(tile['holes'])
        assert sha(hpath)==tile['height_sha256'] and sha(mpath)==tile['holes_sha256']
        files[str(hpath)]=tile['height_sha256'];files[str(mpath)]=tile['holes_sha256']
        y,x,ny,nx=tile['source_window'];n=tile['samples'];assert 0<nx<=n and 0<ny<=n
        mask=np.fromfile(mpath,'u1').reshape(n,n)==0
        r16=np.fromfile(hpath,'<u2').reshape(n,n)
        rows=max(0,min(n,height.shape[0]-y));cols=max(0,min(n,height.shape[1]-x))
        assert (rows,cols)==(ny,nx), 'Clipped source window differs from recorded export'
        native_valid_sum+=int(mask.sum());outside_valid+=int(mask.sum()-mask[:rows,:cols].sum())
        source=height[y:y+rows,x:x+cols];valid=np.isfinite(source);local=mask[:rows,:cols]
        invented+=int(np.count_nonzero(local & ~valid))
        both=local & valid
        decoded=r16[:rows,:cols][both].astype(float)*native['height_quantization_m']+native['source_height_bounds_m'][0]
        max_error=max(max_error,float(np.max(np.abs(decoded-source[both]),initial=0)))
        covered[y:y+rows,x:x+cols]|=local
        expected=np.array([raw['origin_E_N_m'][0]+x*raw['step_m']-native['origin_ENH_m'][0],
            native['origin_ENH_m'][1]-raw['origin_E_N_m'][1]+y*raw['step_m']])*100
        coordinate_errors.append(float(np.max(np.abs(expected-np.array(tile['location_cm'][:2])))))
    raw_valid=0;missing=0;owner_errors=0
    for y in range(0,height.shape[0],256):
        valid=np.isfinite(height[y:y+256]);raw_valid+=int(valid.sum())
        missing+=int(np.count_nonzero(valid & ~covered[y:y+256]))
        owner_errors+=int(np.count_nonzero(valid != (owners[y:y+256]>0)))
    covered_unique=int(covered.sum())
    report={'recorded_unix':time.time(),'passed':missing==invented==outside_valid==owner_errors==0 and max(coordinate_errors)==0 and max_error<=native['height_error_max_bound_m']+1e-9,
        'raw_manifest_sha256':sha(raw_path),'native_manifest_sha256':sha(native_path),
        'raw_array_shape':list(height.shape),'source_asc_files':len(raw['tiles']),
        'source_valid_samples_sum_before_overlap':sum(t['valid_cells'] for t in raw['tiles']),
        'recorded_source_overlap_samples':raw['overlap_cells_checked'],'unique_raw_valid_samples':raw_valid,
        'native_tiles':len(native['tiles']),'native_valid_sample_sum_including_shared_edges':native_valid_sum,
        'unique_native_covered_samples':covered_unique,'duplicate_native_border_samples':native_valid_sum-covered_unique,
        'missing_valid_source_samples':missing,'invented_samples_inside_raw_array':invented,
        'valid_native_samples_outside_raw_array':outside_valid,'raw_owner_vs_height_validity_mismatches':owner_errors,
        'max_native_origin_error_cm':max(coordinate_errors),'max_height_quantization_error_m':max_error,
        'height_quantization_bound_m':native['height_error_max_bound_m'],'step_m':raw['step_m'],
        'native_source_file_sha256':files,'rendering_executed':False,
        'scope':'Original native tiles against the complete existing raw mosaic. This is source data coverage, not runtime residency, final engineering terrain agreement or visual acceptance.',
        'interpretation':'The sum of source ASC valid samples includes overlapping data. Unique source coverage, not the sum before overlap, is the correct comparison with native tile union.'}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='native_source_file_sha256'},indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
