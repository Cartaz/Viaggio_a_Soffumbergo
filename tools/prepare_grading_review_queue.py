"""Prioritize every inventoried earthwork without treating proximity as approval."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--inventory',type=Path,required=True)
    p.add_argument('--structure-manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise RuntimeError('Preserve earlier review queue')
    inventory=json.loads(args.inventory.read_text(encoding='utf-8'))
    manifest=json.loads(args.structure_manifest.read_text(encoding='utf-8'))
    structures=manifest['roadside_structures']
    if inventory['build_id']!=structures['parent_build_id']:
        raise RuntimeError('Inventory must describe the unchanged parent terrain')
    if structures['asphalt_or_native_height_bytes_changed']:
        raise RuntimeError('Terrain changed; regenerate its inventory first')
    controls=structures['config']['controls'];queue=[]
    for i,region in enumerate(inventory['regions']):
        distances=[(math.dist(region['peak_UE_xy_m'],c['center_UE_xy_m']),c) for c in controls]
        distance,nearest=min(distances,key=lambda pair:pair[0])
        nearby=[c['id'] for d,c in distances if d<=c['review_radius_m']]
        queue.append({**region,'inventory_region_index':i,'nearby_structure_controls_at_peak':nearby,
            'nearest_control':nearest['id'],'nearest_control_distance_m':distance,
            'status':'Native geometry and Street View extent/support review required; proximity is not acceptance.'})
    queue.sort(key=lambda r:(abs(r['peak_delta_m']),r['sample_count']),reverse=True)
    report={'build_id':manifest['build_id'],'terrain_parent_build_id':inventory['build_id'],
        'input_sha256':{str(path.resolve()):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [args.inventory,args.structure_manifest]},
        'region_count':len(queue),'major_samples_unique':inventory['major_samples_unique'],
        'regions_peak_over_3m':sum(abs(r['peak_delta_m'])>3 for r in queue),
        'regions_peak_over_3m_outside_local_structure_radii':sum(abs(r['peak_delta_m'])>3 and not r['nearby_structure_controls_at_peak'] for r in queue),
        'regions':queue,'all_earthworks_accepted':False,'world_modified':False,
        'scope':'Spatial review queue for every connected visible grid-change region. A nearby control does not certify observed structure extent, engineering support, visual continuity or safety; a distant peak does not by itself prove a missing structure.'}
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['regions','input_sha256','scope']}))


if __name__=='__main__':main()
