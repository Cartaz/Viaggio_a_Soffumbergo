"""Version a slope-classified earth overlay without changing any geometry."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--parent-draft',type=Path,required=True)
    p.add_argument('--tile',help='Optional local diagnostic; not a full-territory revision')
    args=p.parse_args();parent=args.parent_draft.resolve()
    imported=json.loads((parent/'import_report.json').read_text());original=json.loads(Path(imported['manifest']).read_text())
    if not imported['all_imported']:raise RuntimeError('Verified native parent required')
    config={'earth_full_opacity_below_degrees':15,'earth_zero_opacity_above_degrees':30,
        'opacity_clip':.333,'rule_status':'Engineering classification of the earth overlay; not a surveyed botanical/geological map',
        'tile_diagnostic':args.tile}
    inputs={str(path):sha(path) for path in [Path(imported['manifest']),parent/'circuit_driving_world.json',
        parent/'circuit_itinerary.json',Path(__file__),ROOT/'tools/import_shoulder_material_variant.py']}
    build=hashlib.sha256(json.dumps({'inputs':inputs,'config':config},sort_keys=True).encode()).hexdigest()[:12]
    folder=ROOT/'terrain/road_materials'/build;draft=ROOT/'results/road_drafts'/build
    if folder.exists() or draft.exists():raise RuntimeError('Preserve earlier material variant')
    folder.mkdir(parents=True);draft.mkdir(parents=True)
    m=copy.deepcopy(original);m['build_id']=build
    ids={r['tile'] for r in m['meshes'] if r['kind']=='shoulder'}
    if args.tile:
        if args.tile not in ids:raise ValueError('No shoulder in selected tile')
        ids={args.tile}
    for tile in m['tiles']:
        if tile['id'] in ids:
            tile['material_parent_map']=tile['map'];tile['map']='/Game/World/Driving/V_'+build+'/Terrain/'+tile['id']
    m['shoulder_material_variant']={'parent_build_id':original['build_id'],'parent_draft':str(parent),
        'parent_manifest':imported['manifest'],'config':config,'input_sha256':inputs,
        'material_asset':'/Game/World/Driving/V_'+build+'/Materials/M_ShoulderSlope',
        'geometry_and_physics_changed':False,'full_territory_variant':not args.tile}
    manifest=folder/'manifest.json';manifest.write_text(json.dumps(m,indent=2))
    world=json.loads((parent/'circuit_driving_world.json').read_text());world['build_id']=build
    maps={t['id']:t['map'] for t in m['tiles']}
    for tile in world['tiles']:tile['map']=maps[tile['id']]
    (draft/'circuit_driving_world.json').write_text(json.dumps(world))
    route=json.loads((parent/'circuit_itinerary.json').read_text());route['build_id']=build
    (draft/'circuit_itinerary.json').write_text(json.dumps(route))
    report={'build_id':build,'parent_build_id':original['build_id'],'manifest':str(manifest),'draft':str(draft),
        'change_kind':'slope_classified_earth_material','changed_tiles':sorted(ids),'geometry_changed':False,
        'diagnostic_only':bool(args.tile),'activated':False}
    (draft/'structure_preparation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
