"""Independently check a material-only derivative against its native parent."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--draft',type=Path,required=True)
    args=parser.parse_args();draft=args.draft.resolve();out=draft/'structure_geometry_audit.json'
    if out.exists():raise RuntimeError('Preserve the earlier audit')
    prepared=read(draft/'structure_preparation.json');m=read(prepared['manifest'])
    variant=m['shoulder_material_variant'];parent=read(variant['parent_manifest'])
    parent_draft=Path(variant['parent_draft']);base_audit=read(parent_draft/'structure_geometry_audit.json')
    imported=read(draft/'import_report.json');native=read(imported['journal'])
    changed={t['id'] for t in m['tiles'] if t.get('material_parent_map')}
    expected={r['tile'] for r in parent['meshes'] if r['kind']=='shoulder'}
    normalized=copy.deepcopy(m);normalized['build_id']=parent['build_id'];normalized.pop('shoulder_material_variant')
    for tile in normalized['tiles']:
        if tile['id'] in changed:tile['map']=tile.pop('material_parent_map')
    world=read(draft/'circuit_driving_world.json');oldworld=read(parent_draft/'circuit_driving_world.json')
    world['build_id']=oldworld['build_id'];oldmaps={t['id']:t['map'] for t in oldworld['tiles']}
    worldmaps_match=all(t['map']==next(v['map'] for v in m['tiles'] if v['id']==t['id']) for t in world['tiles'])
    for tile in world['tiles']:tile['map']=oldmaps[tile['id']]
    route=read(draft/'circuit_itinerary.json');oldroute=read(parent_draft/'circuit_itinerary.json')
    route['build_id']=oldroute['build_id']
    checks={
        'parent_geometry_audit_matches':base_audit['passed'] and base_audit['build_id']==parent['build_id'],
        'manifest_changes_limited_to_material_and_map_namespace':normalized==parent,
        'all_mesh_source_bytes_preserved':all(sha(r['source'])==r['sha256'] for r in m['meshes']),
        'all_native_height_and_visibility_bytes_preserved':all(sha(t['heightmap'])==t['height_sha256'] and sha(t['holes'])==t['holes_sha256'] for t in m['tiles']),
        'runtime_world_only_renamed':world==oldworld and worldmaps_match,
        'original_itinerary_preserved':route==oldroute,
        'versioned_inputs_unchanged':all(sha(p)==value for p,value in variant['input_sha256'].items()),
        'native_import_complete':imported['all_imported'] and imported['build_id']==m['build_id'] and native['all_imported'] and native['build_id']==m['build_id'],
        'parent_assets_and_active_files_unchanged':native['protected_files_unchanged'] and all(sha(p)==value for p,value in native['protected_before'].items()),
        'physical_material_preserved':native['physical_material_preserved'],
        'all_changed_component_physics_preserved':set(native['tiles'])==changed and all(t['component_physics_preserved'] for t in native['tiles'].values()),
        'whole_territory_overlay_coverage':changed==expected and variant['full_territory_variant'] and not prepared['diagnostic_only']}
    report={'build_id':m['build_id'],'parent_build_id':parent['build_id'],'passed':all(checks.values()),
        'checks':checks,'changed_tiles':len(changed),'mesh_sources_checked':len(m['meshes']),
        'native_height_tiles_checked':len(m['tiles']),'parent_geometry_audit':str(parent_draft/'structure_geometry_audit.json'),
        'native_import_journal':imported['journal'],
        'scope':'Exact geometry/physics preservation audit; rendered material, roadside continuity and complete driving regression remain separate.'}
    out.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
