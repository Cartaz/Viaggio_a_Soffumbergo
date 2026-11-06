"""Isolate full-world PCG levels while retaining every parent driving asset."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(); p.add_argument('--parent-draft', type=Path, required=True)
    p.add_argument('--masks', type=Path, required=True); args = p.parse_args()
    parent = args.parent_draft.resolve(); imported = json.loads((parent/'import_report.json').read_text())
    assert imported['all_imported']
    original_path = Path(imported['manifest']); original = json.loads(original_path.read_text())
    masks = json.loads(args.masks.read_text()); assert masks['parent_build_id'] == original['build_id']
    audit_path = args.masks.parent/'mask_audit.json'; assert json.loads(audit_path.read_text())['passed']
    asset_report = ROOT/'results/world_foliage_asset_probe_20261024_v1.json'
    assert json.loads(asset_report.read_text())['passed']
    inputs = [original_path, args.masks, audit_path, asset_report, Path(__file__), ROOT/'tools/import_world_vegetation.py',
              parent/'circuit_driving_world.json', parent/'circuit_itinerary.json',
              ROOT/'Unreal/Source/SoffumbergoTerrainEditor/ProceduralFoliage.cpp', ROOT/'Unreal/Source/SoffumbergoTerrainEditor/LidarTerrainLibrary.h',
              ROOT/'Unreal/Source/SoffumbergoLab/LidarVegetation.cpp', ROOT/'Unreal/Source/SoffumbergoLab/LidarVegetation.h',
              ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoTerrainEditor.dll', ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoLab.dll']
    signatures = {str(p.resolve()): sha(p) for p in inputs}
    build = hashlib.sha256(json.dumps(signatures, sort_keys=True).encode()).hexdigest()[:12]
    folder = ROOT/'terrain/world_vegetation'/build; draft = ROOT/'results/road_drafts'/build
    if folder.exists() or draft.exists(): raise RuntimeError('Preserve previous PCG candidate')
    folder.mkdir(parents=True); draft.mkdir(parents=True)
    m = copy.deepcopy(original); m['build_id'] = build
    by_id = {t['tile']: t for t in masks['tiles']}; changed = []
    for tile in m['tiles']:
        if any(b['allowed_cells'] for b in by_id[tile['id']]['branches'].values()):
            changed.append(tile['id'])
            tile['vegetation_parent_map'] = tile['map']; tile['map'] = '/Game/World/Driving/P_'+build+'/Terrain/'+tile['id']
    m['vegetation'] = {'parent_build_id': original['build_id'], 'parent_manifest': str(original_path), 'parent_draft': str(parent),
                       'mask_manifest': str(args.masks.resolve()), 'input_sha256': signatures, 'changed_tiles': changed,
                       'config': masks['config'], 'asset_probe': str(asset_report),
                       'scope': 'Native PCG on every eligible sector of the complete 113-tile world. Unknown/excluded cover stays empty. Existing road, terrain, structures, route and original sources are unchanged.',
                       'artistic_quality_approved': False, 'native_generation_complete': False}
    m['report'].update(build_id=build, native_imported=False, full_lap_driven=False)
    manifest = folder/'manifest.json'; manifest.write_text(json.dumps(m, indent=2))
    world = json.loads((parent/'circuit_driving_world.json').read_text()); world['build_id'] = build
    maps = {t['id']: t['map'] for t in m['tiles']}
    for tile in world['tiles']: tile['map'] = maps[tile['id']]
    (draft/'circuit_driving_world.json').write_text(json.dumps(world))
    route = json.loads((parent/'circuit_itinerary.json').read_text()); route['build_id'] = build
    (draft/'circuit_itinerary.json').write_text(json.dumps(route))
    result = {'build_id': build, 'parent_build_id': original['build_id'], 'manifest': str(manifest), 'draft': str(draft),
              'change_kind': 'whole_world_native_pcg', 'eligible_tiles': len(changed), 'all_source_tiles': len(m['tiles']), 'activated': False}
    (draft/'structure_preparation.json').write_text(json.dumps(result, indent=2)); print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
