"""Exact source samples -> a supported 505x505 Landscape. No terrain noise/resampling."""
import argparse
from array import array
import hashlib
import json
from pathlib import Path
import sys

def prepare(source, output, row=1000, col=900):
    output.mkdir(parents=True, exist_ok=True)
    header = {}
    rows = []
    with source.open(encoding="ascii") as stream:
        for _ in range(6):
            key, value = stream.readline().split()
            header[key.lower()] = float(value)
        for index, line in enumerate(stream):
            if row <= index < row+505:
                values = [float(v) for v in line.split()]
                if len(values) != int(header['ncols']):
                    raise ValueError('Unexpected source row length')
                rows.append(values[col:col+505])
    if len(rows) != 505 or any(len(r) != 505 for r in rows):
        raise ValueError('Crop is outside source coverage')
    heights = [v for r in rows for v in r]
    import math
    if any(not math.isfinite(v) or v == header['nodata_value'] for v in heights):
        raise ValueError('NoData or nonfinite heights: no invented fill')
    lo, hi = min(heights), max(heights)
    if hi <= lo:
        raise ValueError('This converter requires a nonflat source')
    step = header['cellsize']
    e0 = header.get('xllcenter', header.get('xllcorner', 0)+step/2)+col*step
    n0 = header.get('yllcenter', header.get('yllcorner', 0)+step/2)+(header['nrows']-1-row)*step
    h0 = rows[0][0]
    quant = (hi-lo)/65535
    encoded = array('H', (round((h-lo)/quant) for h in heights))
    zscale = quant*100*128
    zoffset = (lo-h0)*100+32768/128*zscale
    error = max(abs(((v-32768)/128*zscale+zoffset)/100+h0-h) for v,h in zip(encoded,heights))
    if error > quant/2+1e-9:
        raise ValueError('Height reconstruction failed')
    if sys.byteorder != 'little':
        encoded.byteswap()
    path = output/'Valle_505.r16'
    path.write_bytes(encoded.tobytes())
    report = {
        'source':str(source.resolve()), 'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'source_header':header,'crop_row_col_count':[row,col,505],
        'horizontal_crs':'EPSG:6708 as recorded in the source provenance',
        'vertical_datum':'ellipsoidal, no vertical datum conversion',
        'origin_ENH_m':[e0,n0,h0], 'ue_axes':'X east, Y south, Z up; centimetres',
        'geographic_mapping':'E=E0+Xcm/100; N=N0-Ycm/100; H=H0+Zcm/100',
        'samples_per_side':505,'spacing_m':step,'extent_m':[504*step,504*step],
        'height_min_max_m':[lo,hi],'height_quantization_m':quant,
        'roundtrip_max_error_m':error,'resampling':False,'noise':False,
        'landscape':{'components_xy':[8,8],'sections_per_component':1,'quads_per_section':63,
                     'xy_scale_cm':step*100,'z_scale':zscale,'actor_z_cm':zoffset},
        'ground_only':True,'vegetation_positions_observed':False,'road_surface_verified':False,
        'unreal_import_verified':False,'collision_verified':False,
        'r16_sha256':hashlib.sha256(path.read_bytes()).hexdigest()
    }
    (output/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'heightmap':str(path),'extent_m':report['extent_m'],'max_error_m':error}))

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    prepare(args.source,args.output)
