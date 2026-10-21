"""Add the circuit inspector; upgrade only the known previous Valle camera script.

Preflight checks all files before writing. Existing user edits abort rather than
being overwritten. Raw DTM, vehicle/character files, branch and F5 are untouched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_VALLE_SHA256 = '1a2529b24ec63ce950c1fed1f638a7164c668a2f21e707e9f5183953e99e4d27'
FILES = [
    'data/config/circuit_3d.json','tools/coffa/dtm_mosaic.py','tools/build_circuit_3d.py',
    'tools/check_circuit_3d.py','tools/validate_circuit.py','tools/sync_circuit_local.py',
    'tools/blender/build_circuit.py','tools/blender/build_valle.py','tests/test_dtm_mosaic.py',
    'godot/scenes/circuit.tscn','godot/scripts/circuit.gd','godot/scripts/circuit_mesh.gd',
    'godot/scripts/circuit_sector.gd','godot/scripts/valle_content.gd','godot/scripts/valle.gd',
    'godot/scripts/circuit.gd.uid','godot/scripts/circuit_mesh.gd.uid','godot/scripts/circuit_sector.gd.uid',
    'godot/scripts/valle_content.gd.uid','godot/tests/circuit_check.gd','godot/tests/circuit_mesh_check.gd',
    'godot/tests/circuit_check.gd.uid','godot/tests/circuit_mesh_check.gd.uid',
    'docs/CIRCUITO_3D.md','reports/CIRCUITO_3D_VERIFICA.json',
]


def normalized_digest(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def sync(target,godot):
    target = target.resolve()
    if target == ROOT or not (target/'project.godot').is_file() or not godot.is_file():
        raise ValueError('Expected a distinct existing project and a Godot executable')
    for relative in ['data/geography/osm_survey.geojson','data/geography/circuit_dtm_catalog_20261020.json']:
        if normalized_digest(target/relative) != normalized_digest(ROOT/relative):
            raise ValueError('Existing geography differs: '+relative)
    manifest = json.loads((ROOT/'build/circuit/manifest.json').read_text(encoding='utf-8'))
    additions = FILES+['build/circuit/manifest.json','build/circuit/generation_report.json']
    for entry in manifest['sectors']:
        relative = Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts or relative.parts[0] != 'datasets':
            raise ValueError('Unsafe generated path')
        additions.append(str(Path('build/circuit')/relative))
    receipt_path = target/'build/circuit_sync_receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {'files':{}}
    changes = []
    for relative in additions:
        source,dest = ROOT/relative,target/relative
        if not dest.resolve().is_relative_to(target):
            raise ValueError('Target path escaped project')
        if dest.exists() and dest.read_bytes() != source.read_bytes():
            known = relative == 'godot/scripts/valle.gd' and normalized_digest(dest) == PREVIOUS_VALLE_SHA256
            known = known or receipt['files'].get(relative) == normalized_digest(dest)
            if not known and normalized_digest(dest) != normalized_digest(source):
                raise FileExistsError('Existing differing file preserved: '+str(dest))
        if not dest.exists() or dest.read_bytes() != source.read_bytes():
            changes.append(relative)
    launcher = target/'Avvia circuito 3D.cmd'
    command = '@echo off\r\n"'+str(godot.resolve())+'" --path "%~dp0." res://godot/scenes/circuit.tscn\r\n'
    if launcher.exists() and launcher.read_text() != command.replace('\r\n','\n'):
        raise FileExistsError('Existing launcher preserved')
    before_scene = (target/'project.godot').read_bytes()
    for relative in changes:
        dest = target/relative
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,dest)
    (target/'build/.gdignore').touch()
    launcher.write_bytes(command.encode('utf-8'))
    marker = '## Circuito 3D 0.1 — corridoio del terreno'
    for relative in ['README.md','docs/ROADMAP.md']:
        dest = target/relative
        if marker not in dest.read_text(encoding='utf-8'):
            with dest.open('a',encoding='utf-8') as stream:
                stream.write('\n\n'+marker+'\n\n352 settori con dettaglio/collisioni a caricamento progressivo, '
                             'fonti per vertice e asse OSM provvisorio. Avvio con `Avvia circuito 3D.cmd`; '
                             'procedura e limiti in `docs/CIRCUITO_3D.md`. Auto, personaggi e F5 conservati.\n')
    if before_scene != (target/'project.godot').read_bytes():
        raise RuntimeError('Unexpected main project change')
    receipt_path.write_text(json.dumps({'schema_version':1,'files':{
        p:normalized_digest(target/p) for p in additions}},indent=2)+'\n',encoding='utf-8')
    report = {'target':str(target),'files_added_or_known_upgrade':changes,'build_id':manifest['build_id'],
              'default_scene_changed':False,'original_rasters_changed':False,
              'source_upgrade_scope':'Known Valle 0.1 camera wrapper plus new circuit files only'}
    output = ROOT/'build/circuit_validation/local_sync.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'target':str(target),'files_updated':len(changes),'build_id':manifest['build_id']},indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,required=True)
    parser.add_argument('--godot',type=Path,required=True)
    args = parser.parse_args()
    sync(args.target,args.godot)
