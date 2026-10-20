"""Add Valle to an existing Windows checkout without replacing unrelated work.

Copies only the explicit Valle file list. A differing existing source aborts the
preflight. Generated data stays local under build/. Does not switch branch or F5.
"""
import argparse
import json
from pathlib import Path
import shutil

from build_valle_3d import ROOT, sha

FILES = [
    'data/config/valle_3d.json', 'requirements-terrain.txt',
    'godot/scenes/valle.tscn', 'godot/scripts/valle.gd', 'godot/scripts/valle_sector.gd',
    'godot/tests/valle_check.gd', 'tools/coffa/terrain.py', 'tools/import_valle_lidar05.py',
    'tools/build_valle_3d.py', 'tools/check_valle_3d.py', 'tools/validate_valle.py',
    'tools/sync_valle_local.py', 'tools/blender/build_valle.py', 'tests/test_terrain.py',
    'docs/VALLE_3D.md', 'reports/VALLE_3D_VERIFICA.json',
    'tools/catalog_circuit_dtm.py', 'tests/test_circuit_dtm.py',
    'tools/register_dtm.py',
    'data/geography/circuit_dtm_catalog_20261020.json',
    'data/geography/circuito_osm_candidate_20261020.geojson',
    'data/geography/lidar05_valle_tile_manifest_20261020.json',
    'docs/DTM_CIRCUITO_COMPLETO.md',
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--godot', type=Path, required=True)
    args = parser.parse_args()
    target = args.target.resolve()
    if not (target/'project.godot').is_file() or target == ROOT:
        raise ValueError('Expected a distinct existing Godot project')
    if not args.godot.is_file():
        raise FileNotFoundError(args.godot)
    # A different OSM snapshot would invalidate building IDs and alignment.
    osm = 'data/geography/osm_survey.geojson'
    if sha(target/osm) != sha(ROOT/osm):
        raise ValueError('Target OSM differs; integrate geography manually first')
    additions = FILES + ['build/valle/valle_scene.json', 'build/valle/generation_report.json']
    for relative in additions:
        destination = target/relative
        if destination.exists() and destination.read_bytes() != (ROOT/relative).read_bytes():
            raise FileExistsError('Existing differing file preserved: '+str(destination))
    launcher = target/'Avvia Valle 3D.cmd'
    command = '@echo off\r\n"'+str(args.godot.resolve())+'" --path "%~dp0." res://godot/scenes/valle.tscn\r\n'
    if launcher.exists() and launcher.read_text() != command.replace('\r\n', '\n'):
        raise FileExistsError('Existing launcher preserved: '+str(launcher))
    copied = []
    for relative in additions:
        destination = target/relative
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/relative, destination)
            copied.append(relative)
    (target/'build/.gdignore').touch()
    launcher.write_bytes(command.encode('utf-8'))
    marker = '## Valle 3D 0.1 — integrazione del 20 ottobre 2026'
    for relative in ['README.md', 'docs/ROADMAP.md']:
        destination = target/relative
        text = destination.read_text(encoding='utf-8')
        if marker not in text:
            with destination.open('a', encoding='utf-8') as fh:
                fh.write('\n\n'+marker+'\n\nPrototipo geografico separato, avviabile con `Avvia Valle 3D.cmd`. '
                         '36 settori DTM, 91 sagome OSM, strade provvisorie; rigenerazione e limiti in '
                         '`docs/VALLE_3D.md`. Auto, personaggi, scena iniziale e lavori precedenti conservati.\n')
    ignore = target/'.gitignore'
    patterns = ['/build/', '*.asc', '*.tif', '*.tiff', '*.las', '*.laz', 'download-*.zip']
    existing = ignore.read_text(encoding='utf-8').splitlines()
    missing = [pattern for pattern in patterns if pattern not in existing]
    if missing:
        with ignore.open('a', encoding='utf-8') as fh:
            fh.write('\n# Valle: dati originali e derivati locali\n'+'\n'.join(missing)+'\n')
    result = {'target': str(target), 'added': copied, 'osm_match': True,
              'existing_source_replaced': False, 'default_scene_changed': False}
    (ROOT/'build/valle_validation').mkdir(parents=True, exist_ok=True)
    (ROOT/'build/valle_validation/local_sync.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
