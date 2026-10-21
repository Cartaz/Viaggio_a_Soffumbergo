"""Deterministic construction, unchanged sources, real Godot contacts and Blender."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--godot', type=Path, required=True)
    parser.add_argument('--blender', type=Path, required=True)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    output = ROOT/'build/construction_validation'
    output.mkdir(parents=True, exist_ok=True)
    report_path = output/'validation_report.json'
    steps = []
    report_path.write_text('{"passed":false}\n')
    immutable = [ROOT/'build/circuit'/name for name in
                 ['manifest.json', 'pilot_manifest.json', 'pilot_road.json', 'parking_manifest.json', 'parking_road.json']]
    before = {str(p.relative_to(ROOT)):sha(p) for p in immutable}
    catalog = json.loads((ROOT/'data/geography/circuit_dtm_catalog_20261020.json').read_bytes())
    for tile in catalog['tiles']:
        assert sha(args.input_dir/tile['filename']) == tile['sha256'], 'Changed original DTM'

    def run(name, command):
        start = time.monotonic()
        result = subprocess.run([str(v) for v in command], cwd=ROOT, capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=600)
        log = result.stdout+result.stderr
        (output/(name+'.log')).write_text(log, encoding='utf-8')
        errors = bool(re.search(r'(^|\n)(SCRIPT ERROR:|ERROR:|Traceback|WARNING: ObjectDB)', log))
        step = {'name':name, 'exit_code':result.returncode, 'engine_errors':errors,
                'seconds':round(time.monotonic()-start, 3)}
        steps.append(step)
        report_path.write_text(json.dumps({'passed':False, 'steps':steps}, indent=2)+'\n')
        print(json.dumps(step), flush=True)
        if result.returncode or errors:
            raise RuntimeError('Construction validation failed: '+name)

    run('python', [sys.executable, 'tools/check_project.py'])
    gd = sorted(str(p.relative_to(ROOT)) for p in (ROOT/'godot').rglob('*.gd'))
    for name, extra in [('gdparse', []), ('gdformat', ['--check']), ('gdlint', [])]:
        program = shutil.which(name) or Path(sys.executable).parent/(name+'.exe')
        run(name, [program]+extra+gd)
    run('generate', [sys.executable, 'tools/build_circuit_construction.py'])
    manifest = ROOT/'build/circuit/construction_manifest.json'
    document = json.loads(manifest.read_bytes())
    paths = [manifest, ROOT/'build/circuit/construction_report.json']
    paths += [ROOT/'build/circuit'/e['path'] for e in document['sectors']]
    paths += [ROOT/'build/circuit'/e['path'] for e in document['engineering_construction']['road_sectors']]
    first = {str(p.relative_to(ROOT)):sha(p) for p in paths}
    run('regenerate', [sys.executable, 'tools/build_circuit_construction.py'])
    assert first == {str(p.relative_to(ROOT)):sha(p) for p in paths}, 'Non-deterministic output'
    run('geometry', [sys.executable, 'tools/check_circuit_construction.py'])
    run('yaris_asset', [sys.executable, 'tools/check_yaris_asset.py'])
    godot = args.godot.resolve()
    run('import', [godot, '--headless', '--path', ROOT, '--editor', '--import', '--quit'])
    script = 'godot/tests/circuit_construction_check.gd'
    run('jolt', [godot, '--headless', '--path', ROOT, '--script', script])
    shutil.copyfile(output/'godot_report.json', output/'godot_headless_report.json')
    if args.capture:
        run('render', [godot, '--path', ROOT, '--windowed', '--resolution', '1280x720', '--script', script, '--', '--capture'])
        shutil.copyfile(output/'godot_report.json', output/'godot_render_report.json')
    run('blender', [args.blender.resolve(), '--background', '--factory-startup', '--python', 'tools/blender/build_circuit_construction.py'])
    assert before == {str(p.relative_to(ROOT)):sha(p) for p in immutable}, 'Original/pilot derivatives changed'
    for tile in catalog['tiles']:
        assert sha(args.input_dir/tile['filename']) == tile['sha256'], 'Original raster changed'
    report = {'passed':True, 'steps':steps, 'construction_manifest_sha256':sha(manifest),
              'immutable_inputs':before, 'raw_tiles_checked_before_and_after':len(catalog['tiles']),
              'deterministic_files':len(first), 'full_lap_driven':False}
    report_path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
