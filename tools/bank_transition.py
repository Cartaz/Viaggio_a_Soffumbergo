"""Bounded road-relative subgrade on an independently observed cut bank.

Original LiDAR and asphalt are immutable. This replaces the height-dependent
transition width with one declared engineering section, restricted to one side
of the reviewed road. It does not smooth the measured terrain.
"""
import numpy as np
import shapely
from road_clearance import support_caps


def smooth(t):
    t = np.clip(t, 0, 1)
    return t*t*(3-2*t)


def refit(manifest, source_manifest, road, config):
    tile = next(t for t in manifest['tiles'] if t['id'] == config['tile'])
    source = next(t for t in source_manifest['tiles'] if t['id'] == tile['id'])
    n = tile['samples']; step = tile['xy_scale_cm']/100
    old = np.fromfile(tile['heightmap'], '<u2').reshape(n, n)
    raw = np.fromfile(source['heightmap'], '<u2').reshape(n, n)
    holes = np.fromfile(tile['holes'], 'u1').reshape(n, n)
    quant = source_manifest['height_quantization_m']
    zero = source_manifest['source_height_bounds_m'][0]-manifest['origin_ENH_m'][2]
    sections = manifest['rockfall_edges']['net_bank_sections']
    edge = np.asarray(sections['asphalt_edge_UE_xy_m'])
    normals = np.asarray(sections['uphill_UE_xy_unit'])
    station = np.asarray(sections['station_m'])
    segments = shapely.linestrings(np.stack([edge[:-1], edge[1:]], axis=1))
    tree = shapely.STRtree(segments)
    width = config['outer_offset_m']
    lo = edge.min(0)-width-step; hi = edge.max(0)+width+step
    origin = np.asarray(tile['bounds_xy_cm'][:2])/100
    lower = np.maximum(0, np.floor((lo-origin)/step).astype(int))
    upper = np.minimum(n-1, np.ceil((hi-origin)/step).astype(int))
    xx, yy = np.meshgrid(np.arange(lower[0], upper[0]+1), np.arange(lower[1], upper[1]+1))
    col = xx.ravel(); row = yy.ravel(); p = origin+np.c_[col, row]*step
    pairs = tree.query_nearest(shapely.points(p), all_matches=False)
    index = np.empty(len(p), int); index[pairs[0]] = pairs[1]
    a = edge[index]; delta = edge[index+1]-a
    fraction = np.clip(((p-a)*delta).sum(1)/(delta*delta).sum(1), 0, 1)
    near = a+fraction[:, None]*delta
    normal = normals[index]*(1-fraction[:, None])+normals[index+1]*fraction[:, None]
    along = station[index]*(1-fraction)+station[index+1]*fraction
    uphill = ((p-near)*normal).sum(1)
    road_z, distance = road.sample(p*100, clamp_to_triangle=True)
    road_z /= 100; distance /= 100
    fade = smooth((along-station[0])/config['end_fade_m'])*smooth((station[-1]-along)/config['end_fade_m'])
    eligible = (uphill > 0) & (distance > 0) & (distance < width) & (fade > 0) & (holes[row, col] == 0)
    p = p[eligible]; row = row[eligible]; col = col[eligible]
    distance = distance[eligible]; road_z = road_z[eligible]; fade = fade[eligible]
    source_z = raw[row, col].astype(float)*quant+zero
    old_z = old[row, col].astype(float)*quant+zero
    toe = road_z-config['subgrade_clearance_m']
    weight = smooth((distance-config['toe_offset_m'])/(width-config['toe_offset_m']))
    # No new embankment on this observed uphill cut: retain source wherever
    # the source happens to be below the proposed engineering section.
    desired = np.minimum(source_z, toe+(source_z-toe)*weight)
    # Join the existing outer derivative continuously, including portions
    # where its earlier gentle-bank transition extends past this local work.
    feather = smooth((width-distance)/config['outer_feather_m'])
    desired = old_z+(desired-old_z)*fade*feather
    supported = distance <= step*np.sqrt(2)+1.e-8
    faces = road.faces[:, :, [0, 2, 1]]/100
    polygons = shapely.polygons(faces[:, :, [0, 2]])
    caps = support_caps(p[supported, 0], p[supported, 1], faces,
                        shapely.STRtree(polygons), polygons, step,
                        config['subgrade_clearance_m'])
    desired[supported] = np.minimum(desired[supported], caps)
    result = old.copy()
    codes = np.floor((desired-zero)/quant).astype(int)
    if np.any((codes < 0) | (codes > 65535)):
        raise ValueError('Cut outside source R16 quantizer')
    result[row, col] = codes
    changed = result != old
    # These exact coordinates are retained for an independent scope audit.
    return tile, result, {
        'eligible_samples': len(p), 'changed_samples': int(changed.sum()),
        'max_delta_from_parent_m': float(np.abs(result.astype(float)-old).max()*quant),
        'max_delta_from_source_m': float(np.abs(result.astype(float)-raw).max()*quant),
        'changed_UE_xy_m': (origin+np.argwhere(changed)[:, ::-1]*step).tolist(),
        'reviewed_station_range_m': [float(station[0]), float(station[-1])],
        'engineering_dimensions_measured': False,
    }
