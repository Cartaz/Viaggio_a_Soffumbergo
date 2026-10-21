"""Regenerate ramps twice; verify source preservation, Jolt, recovery and Blender."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--godot', type=Path, required=True)
    parser.add_argument('--blender', type=Path, required=True)
    parser.add_argument('--project', type=Path, required=True, help='Local project with the approved final vehicle assembly')
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    output = ROOT/'build/shoulder_validation'
    output.mkdir(parents=True, exist_ok=True)
    immutable = [ROOT/'build/circuit'/name for name in ['manifest.json', 'construction_manifest.json']]
    construction = json.loads(immutable[1].read_bytes())
    immutable += [ROOT/'build/circuit'/e['path'] for e in construction['sectors']+construction['engineering_construction']['road_sectors']]
    before = {str(p.relative_to(ROOT)):sha(p) for p in immutable}
    steps = []

    def run(name, command):
        result = subprocess.run([str(v) for v in command], cwd=ROOT, capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=1800)
        log = result.stdout+result.stderr
        (output/(name+'.log')).write_text(log, encoding='utf-8')
        errors = bool(re.search(r'(^|\n)(SCRIPT ERROR:|ERROR:|Traceback|WARNING: ObjectDB)', log))
        steps.append({'name':name, 'exit_code':result.returncode, 'engine_errors':errors})
        (output/'validation_report.json').write_text(json.dumps({'passed':False, 'steps':steps}, indent=2)+'\n')
        if result.returncode or errors:
            raise RuntimeError('Shoulder validation failed: '+name)

    run('python', [sys.executable, 'tools/check_project.py'])
    run('generate', [sys.executable, 'tools/build_circuit_shoulders.py'])
    manifest = ROOT/'build/circuit/shoulders.json'
    doc = json.loads(manifest.read_bytes())
    paths = [manifest]+[ROOT/'build/circuit'/e['path'] for e in doc['sectors']]
    first = {str(p.relative_to(ROOT)):sha(p) for p in paths}
    run('regenerate', [sys.executable, 'tools/build_circuit_shoulders.py'])
    assert first == {str(p.relative_to(ROOT)):sha(p) for p in paths}, 'Non-deterministic shoulders'
    run('road_geometry', [sys.executable, 'tools/check_circuit_construction.py'])
    run('geometry', [sys.executable, 'tools/check_circuit_shoulders.py'])
    gd = sorted((ROOT/'godot').rglob('*.gd'))
    for command, extra in [('gdparse', []), ('gdformat', ['--check']), ('gdlint', [])]:
        run(command, [Path(sys.executable).parent/(command+'.exe')]+extra+gd)
    godot = args.godot.resolve()
    project = args.project.resolve()
    if not (project/'project.godot').is_file():
        raise ValueError('Approved project required')
    run('sync_approved', [sys.executable, 'tools/sync_circuit_construction_local.py', '--target', project, '--godot', godot])
    script = 'godot/tests/circuit_shoulders_check.gd'
    run('headless120', [godot, '--headless', '--path', project, '--script', script, '--', '--output=build/shoulder_validation/final120'])
    run('headless60', [godot, '--headless', '--path', project, '--script', script, '--', '--hz=60', '--output=build/shoulder_validation/final60'])
    if args.capture:
        run('render', [godot, '--path', project, '--windowed', '--resolution', '1280x720', '--script', script,
                       '--', '--capture', '--output=build/shoulder_validation/final_render'])
    run('snapshot_approved_model', [godot, '--headless', '--path', project, '--script', 'godot/tests/final_vehicle_snapshot.gd'])
    run('blender', [args.blender.resolve(), '--background', '--factory-startup', '--python', 'tools/blender/build_circuit_construction.py',
                    '--', '--approved-vehicle-snapshot', project/'build/final_vehicle_validation/final_vehicle.glb'])
    assert before == {str(p.relative_to(ROOT)):sha(p) for p in immutable}, 'Source/road/earthworks changed'
    result = {'passed':True, 'steps':steps, 'shoulders_manifest_sha256':sha(manifest),
              'approved_project_required':True,
              'immutable_files_verified':len(before), 'deterministic_files':len(paths),
              'full_lap_driven':False, 'real_roadside_verified':False}
    (output/'validation_report.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
