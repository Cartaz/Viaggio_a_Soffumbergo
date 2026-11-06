"""CPU-only radial height diagnostic against recorded native gallery viewpoints.

This models bare-ground angular coverage, not final pixels or occlusion by assets.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import time

import numpy as np
from prepare_reentry_checks import NativeGround

ROOT = Path(__file__).resolve().parents[1]


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(); p.add_argument('--draft', type=Path, required=True)
    p.add_argument('--gallery', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists(): raise RuntimeError('Preserve previous diagnostic')
    prep = json.loads((args.draft/'structure_preparation.json').read_text())
    manifest_path = Path(prep['manifest']); m = json.loads(manifest_path.read_text())
    gallery_report = json.loads((args.gallery/'report.json').read_text())
    assert gallery_report['passed'] and gallery_report['build_id'] == m['build_id']
    args.output.mkdir(parents=True)
    code = ROOT/'Unreal/Source/SoffumbergoLab/CircuitTerrainWorld.h'
    text = code.read_text()
    load = float(re.search(r'LoadRadiusCm=(\d+)', text)[1])/100
    unload = float(re.search(r'UnloadRadiusCm=(\d+)', text)[1])/100
    bounds = np.array([t['bounds_xy_cm'] for t in m['tiles']])/100
    ground = NativeGround(m)
    distances = np.arange(10, 8000+1, 10, dtype=float)
    headings = np.arange(360, dtype=float)
    direction = np.column_stack([np.cos(np.radians(headings)), np.sin(np.radians(headings))])
    evidence = {}; views = []
    for case in sorted(args.gallery.iterdir()):
        if not case.is_dir(): continue
        launch_path = case/'launch_manifest.json'
        if not launch_path.exists(): continue
        launch = json.loads(launch_path.read_text())
        meta_path = case/('gallery_'+case.name+'.json')
        meta = json.loads(meta_path.read_text())
        value = meta['external_camera_final_location_cm']
        observer = np.array([float(re.search(k+r'=([-+\d.]+)', value)[1]) for k in ['X','Y','Z']])/100
        # Exact recorded final external position; source streaming uses pawn XY.
        pawn = np.array(launch['initial_position_cm'][:2])/100
        delta = np.maximum(np.maximum(bounds[:, :2]-pawn, pawn-bounds[:, 2:]), 0)
        requested = np.linalg.norm(delta, axis=1) <= load
        possible = np.linalg.norm(delta, axis=1) <= unload
        xy = observer[:2]+distances[None, :, None]*direction[:, None, :]
        z = ground.sample(xy.reshape(-1, 2)).reshape(len(headings), -1)
        angles = np.degrees(np.arctan2(z-observer[2], distances[None, :]))
        loaded_mask = np.zeros(z.shape, bool); upper_mask = np.zeros(z.shape, bool)
        for b, req, pos in zip(bounds, requested, possible):
            if not pos: continue
            inside = (xy[:, :, 0]>=b[0]) & (xy[:, :, 0]<b[2]) & (xy[:, :, 1]>=b[1]) & (xy[:, :, 1]<b[3])
            upper_mask |= inside
            if req: loaded_mask |= inside
        valid = np.isfinite(z)
        finite_angles = np.where(valid, angles, -90)
        full_angle = finite_angles.max(axis=1)
        load_angle = np.where(loaded_mask, finite_angles, -90).max(axis=1)
        upper_angle = np.where(upper_mask, finite_angles, -90).max(axis=1)
        far_angle = np.where(~upper_mask, finite_angles, -90).max(axis=1)
        peak = np.argmax(finite_angles, axis=1)
        rows = []
        for i, heading in enumerate(headings):
            indices = np.flatnonzero(valid[i])
            rows.append({'heading_ue_xy_degrees': int(heading), 'full_source_horizon_degrees': float(full_angle[i]),
                'requested_tile_horizon_degrees': float(load_angle[i]), 'all_hysteresis_tile_horizon_degrees': float(upper_angle[i]),
                'beyond_hysteresis_horizon_degrees': float(far_angle[i]),
                'full_horizon_distance_m': float(distances[peak[i]]) if len(indices) else None,
                'last_valid_sample_distance_m': float(distances[indices[-1]]) if len(indices) else None,
                'valid_source_samples': int(len(indices))})
        with (args.output/(case.name+'_radial.csv')).open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
        # Source can still replace blue below an existing skyline even when no
        # farther point exceeds the nearest hill; this is not a pixel count.
        beyond_count = np.sum(valid & ~upper_mask, axis=1)
        item = {'control': case.name, 'observer_final_external_UE_m': observer.tolist(),
                'streaming_reference_initial_pawn_UE_xy_m': pawn.tolist(),
                'requested_tile_ids': [t['id'] for t, yes in zip(m['tiles'], requested) if yes],
                'all_possible_hysteresis_tile_ids': [t['id'] for t, yes in zip(m['tiles'], possible) if yes],
                'headings_with_valid_lidar_beyond_hysteresis_tiles': int(np.count_nonzero(beyond_count)),
                'headings_with_far_source_above_near_horizon_by_0_2_degree': int(np.count_nonzero((far_angle-upper_angle)>0.2)),
                'maximum_far_horizon_gain_degrees': float(np.max(far_angle-upper_angle)),
                'radial_data': str((args.output/(case.name+'_radial.csv')).resolve())}
        views.append(item); evidence[str(launch_path.resolve())] = sha(launch_path); evidence[str(meta_path.resolve())] = sha(meta_path)
    report = {'build_id': m['build_id'], 'recorded_unix': time.time(), 'diagnostic_completed': True,
        'runtime_rendering_executed': False, 'runtime_streaming_visibility_directly_measured': False,
        'source_manifest': str(manifest_path), 'source_manifest_sha256': sha(manifest_path),
        'streaming_source_sha256': sha(code), 'load_radius_m': load, 'unload_radius_m': unload,
        'heading_step_degrees': 1, 'radial_step_m': 10, 'radial_limit_m': 8000,
        'source_height_quantization_m': ground.quant, 'views': views, 'evidence_sha256': evidence,
        'interpretation': 'There is source terrain outside the detailed streaming envelope. A lightweight far representation can restore known relief without keeping all full Landscapes resident. This does not supply terrain beyond source coverage.',
        'limits': ['Bare-earth radial model; not a rendered camera projection and not an explanation of every blue pixel.',
            'Ignores foliage, buildings, road structures and atmospheric occlusion.',
            '10 m sampling can miss narrow peaks or source gaps; diagnostic only.',
            'Recorded final camera and initial pawn can differ after key movements; comparison is approximate.',
            'All tiles inside the unload envelope are an upper bound, not the actual loaded set.',
            'No heights extrapolated outside the original source or through holes.']}
    (args.output/'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'output': str(args.output.resolve()), 'views': [{k:v for k,v in item.items() if k not in ['requested_tile_ids','all_possible_hysteresis_tile_ids','radial_data']} for item in views]}, indent=2))


if __name__ == '__main__': main()
