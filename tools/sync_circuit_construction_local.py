"""Install only owned construction files; preflight preserves private user changes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
FILES = ['data/config/circuit_construction.json', 'tools/coffa/road_construction.py',
         'tools/build_circuit_construction.py', 'tools/check_circuit_construction.py',
         'tools/validate_circuit_construction.py', 'tools/sync_circuit_construction_local.py',
         'tools/blender/build_circuit_construction.py', 'tests/test_road_construction.py',
         'godot/scripts/circuit_construction.gd', 'godot/scripts/circuit_construction.gd.uid',
         'godot/scenes/circuit_construction.tscn', 'godot/tests/circuit_construction_check.gd',
         'godot/tests/circuit_construction_check.gd.uid', 'docs/COSTRUZIONE_CIRCUITO.md',
         'reports/COSTRUZIONE_CIRCUITO_VERIFICA.json', 'build/circuit/construction_manifest.json',
         'build/circuit/construction_report.json', 'build/construction_validation/probes.json',
         'build/construction_validation/circuit_construction.blend',
         'build/construction_validation/blender_report.json']
FILES += ['data/geography/circuit_maneuver_review.json', 'tools/build_circuit_practice.py',
          'tests/test_circuit_practice.py', 'godot/scripts/practice_route.gd',
          'godot/scripts/practice_route.gd.uid', 'godot/scripts/circuit_practice.gd',
          'godot/scripts/circuit_practice.gd.uid', 'godot/scenes/circuit_practice.tscn',
          'godot/tests/circuit_practice_check.gd', 'godot/tests/circuit_practice_check.gd.uid',
          'godot/tests/practice_route_check.gd', 'godot/tests/practice_route_check.gd.uid',
          'docs/PRATICA_CIRCUITO.md', 'reports/PRATICA_CIRCUITO_VERIFICA.json',
          'build/circuit/practice.json']
FILES += ['data/config/circuit_loop.json', 'data/config/circuit_shoulders.json',
          'tools/build_circuit_loop.py', 'tools/coffa/loop_route.py', 'tools/coffa/maneuver_search.py',
          'tools/build_circuit_shoulders.py', 'tools/check_circuit_shoulders.py',
          'tools/coffa/road_shoulders.py', 'tools/validate_circuit_shoulders.py',
          'tests/test_circuit_loop.py', 'tests/test_road_shoulders.py',
          'godot/scripts/circuit_loop.gd', 'godot/scripts/circuit_loop.gd.uid',
          'godot/scripts/construction_surface.gd', 'godot/scripts/construction_surface.gd.uid',
          'godot/scenes/circuit_loop.tscn',
          'godot/shaders/circuit_surface.gdshader', 'godot/shaders/circuit_surface.gdshader.uid',
          'godot/tests/circuit_loop_check.gd', 'godot/tests/circuit_loop_check.gd.uid',
          'godot/tests/circuit_shoulders_check.gd', 'godot/tests/circuit_shoulders_check.gd.uid',
          'godot/tests/final_vehicle_guard.gd',
          'godot/tests/final_vehicle_snapshot.gd',
          'docs/GIRO_COSTRUZIONE.md', 'docs/RACCORDI_E_ASFALTO.md',
          'reports/GIRO_COSTRUZIONE_VERIFICA.json', 'reports/RACCORDI_ASFALTO_VERIFICA.json',
          'build/circuit/loop.json', 'build/circuit/shoulders.json',
          'build/shoulder_validation/probes.json', 'build/shoulder_validation/recovery_route.json']


def digest(path):
    data = path.read_bytes()
    return hashlib.sha256(data if path.suffix == '.blend' else data.replace(b'\r\n', b'\n')).hexdigest()


def sync(target, godot):
    target, godot = target.resolve(), godot.resolve()
    if target == ROOT or not (target/'project.godot').is_file() or not godot.is_file():
        raise ValueError('Distinct existing project and Godot executable required')
    manifest = json.loads((ROOT/'build/circuit/construction_manifest.json').read_bytes())
    source = manifest['engineering_construction']['report']['source_manifest_sha256']
    if hashlib.sha256((target/'build/circuit/manifest.json').read_bytes()).hexdigest() != source:
        raise ValueError('Local original terrain differs; preserved')
    receipt = target/'build/construction_sync_receipt.json'
    owned = json.loads(receipt.read_bytes())['files'] if receipt.exists() else {}
    paths = list(FILES)
    for e in manifest['sectors']+manifest['engineering_construction']['road_sectors']:
        relative = Path(e['path'])
        if relative.is_absolute() or '..' in relative.parts or relative.parts[0] != 'datasets':
            raise ValueError('Unsafe derivative path')
        paths.append(str(Path('build/circuit')/relative))
    shoulders = json.loads((ROOT/'build/circuit/shoulders.json').read_bytes())
    if shoulders['construction_manifest_sha256'] != hashlib.sha256((ROOT/'build/circuit/construction_manifest.json').read_bytes()).hexdigest():
        raise ValueError('Regenerate shoulders before sync')
    for e in shoulders['sectors']:
        relative = Path(e['path'])
        if relative.is_absolute() or '..' in relative.parts or relative.parts[0] != 'datasets':
            raise ValueError('Unsafe shoulder path')
        paths.append(str(Path('build/circuit')/relative))
    changes = []
    for p in paths:
        src, dest = ROOT/p, target/p
        if not dest.resolve().is_relative_to(target):
            raise ValueError('Target escape')
        if dest.exists() and digest(src) != digest(dest):
            if owned.get(p) != digest(dest):
                raise ValueError('Existing user change preserved: '+str(dest))
        if not dest.exists() or src.read_bytes() != dest.read_bytes():
            changes.append(p)
    launchers = {}
    for name, scene in [('Avvia costruzione circuito.cmd', 'circuit_construction'),
                        ('Avvia pratica circuito.cmd', 'circuit_practice'),
                        ('Avvia giro di costruzione.cmd', 'circuit_loop')]:
        launcher = target/name
        command = ('@echo off\r\n"'+str(godot)+'" --path "%~dp0." res://godot/scenes/'+scene+'.tscn\r\n').encode()
        if launcher.exists() and launcher.read_bytes() != command:
            raise ValueError('Existing launcher preserved')
        launchers[launcher] = command
    settings = (target/'project.godot').read_bytes()
    for p in changes:
        dest = target/p
        if dest.exists():
            backup = target/'build/construction_backups'/digest(dest)/p
            backup.parent.mkdir(parents=True, exist_ok=True)
            if not backup.exists():
                shutil.copyfile(dest, backup)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/p, dest)
    for launcher, command in launchers.items():
        launcher.write_bytes(command)
    (target/'build/.gdignore').touch()
    receipt.write_text(json.dumps({'files':{p:digest(target/p) for p in paths}}, indent=2)+'\n', encoding='utf-8')
    assert settings == (target/'project.godot').read_bytes()
    result = {'target':str(target), 'files_updated':len(changes), 'build_id':manifest['engineering_construction']['report']['build_id'],
              'default_scene_changed':False, 'private_assets_changed':False}
    (ROOT/'build/construction_validation/local_sync.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--godot', type=Path, required=True)
    args = parser.parse_args()
    sync(args.target, args.godot)
