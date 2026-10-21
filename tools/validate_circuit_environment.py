"""Rebuild, verify and inspect the environment with the approved private assembly."""
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


def run(command, log, timeout=180):
    result = subprocess.run([str(a) for a in command], cwd=ROOT, capture_output=True,
                            encoding='utf-8', errors='replace', timeout=timeout)
    log.write_text(result.stdout+result.stderr, encoding='utf-8')
    if result.returncode or 'SCRIPT ERROR:' in result.stdout+result.stderr:
        raise ValueError('Check failed: '+str(log)+'\n'+(result.stdout+result.stderr)[-5000:])
    return result.stdout+result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--godot', type=Path, required=True)
    parser.add_argument('--blender', type=Path, required=True)
    args = parser.parse_args()
    target = args.project.resolve()
    if target == ROOT or not (target/'project.godot').is_file():
        raise ValueError('Separate approved private project required')
    out = ROOT/'build/environment_validation'
    out.mkdir(parents=True, exist_ok=True)
    expected = {'yaris_hybrid_red_game.glb', 'pirate_mast_coffa.glb', 'bernie.glb', 'bianca.glb'}
    private = [target/'project.godot', target/'godot/scripts/vehicle_lab.gd', target/'data/config/vehicle_lab.json']
    private += [p for p in (target/'art').rglob('*.glb') if p.name in expected]
    private += [p for p in (target/'godot/assets').rglob('*.glb') if p.name in expected]
    if {p.name for p in private} & expected != expected:
        raise ValueError('Private final assets missing')
    preserved = {p:sha(p) for p in private}
    immutable = {p:sha(p) for p in [ROOT/'build/circuit/manifest.json',
                                    ROOT/'build/circuit/construction_manifest.json',
                                    ROOT/'build/circuit/shoulders.json']}
    run([sys.executable, ROOT/'tools/build_circuit_environment.py'], out/'build_first.log')
    generated = [ROOT/'data/geography/circuit_placeholders.json', ROOT/'reports/CATALOGO_SEGNAPOSTO.html',
                 ROOT/'reports/CATALOGO_SEGNAPOSTO.csv', ROOT/'reports/AMBIENTE_CIRCUITO_CATALOGO.json']
    hashes = {p:sha(p) for p in generated}
    run([sys.executable, ROOT/'tools/build_circuit_environment.py'], out/'build_second.log')
    if hashes != {p:sha(p) for p in generated}:
        raise ValueError('Nondeterministic environment generation')
    checks = run([sys.executable, ROOT/'tools/check_project.py'], out/'source_checks.log')
    scripts = sorted((ROOT/'godot').rglob('*.gd'))
    for tool, extra in [('gdparse', []), ('gdformat', ['--check']), ('gdlint', [])]:
        run([Path(sys.executable).parent/(tool+'.exe'), *extra, *scripts], out/(tool+'.log'))
    run([sys.executable, ROOT/'tools/sync_circuit_construction_local.py', '--target', target,
         '--godot', args.godot], out/'sync.log')
    runtime = {}
    for mode in ['headless', 'render']:
        command = [args.godot, '--path', target]
        command += ['--headless'] if mode == 'headless' else ['--resolution', '1280x720']
        command += ['--script', 'res://godot/tests/circuit_environment_check.gd', '--',
                    '--output=build/environment_validation/'+mode]
        if mode == 'render':
            command += ['--capture']
        run(command, out/(mode+'.log'))
        report = json.loads((target/'build/environment_validation'/mode/'report.json').read_bytes())
        if report['status'] != 'passed' or not report['approved_vehicle']['approved_assembly_loaded']:
            raise ValueError('Approved runtime acceptance failed')
        runtime[mode] = report
    run([args.blender, '-b', '--python', ROOT/'tools/blender/build_circuit_environment.py'], out/'blender.log')
    blender = json.loads((out/'blender_report.json').read_bytes())
    if not blender['passed'] or not blender['approved_assembly_present']:
        raise ValueError('Native Blender acceptance failed')
    if preserved != {p:sha(p) for p in private}:
        raise ValueError('Private assets or settings changed; inspect without overwriting')
    if immutable != {p:sha(p) for p in immutable}:
        raise ValueError('Terrain/road/shoulder input changed')
    catalog = json.loads((ROOT/'data/geography/circuit_placeholders.json').read_bytes())
    evidence = {'schema_version':1, 'status':'passed_visual_blockout_not_metric_reconstruction',
                'catalog_build_id':catalog['build_id'], 'catalog_sha256':hashes[generated[0]],
                'deterministic_regeneration':True,
                'python_tests_passed':int(re.search(r'Ran (\d+) tests', checks)[1]),
                'gdtoolkit_all_scripts_passed':True,
                'godot':runtime, 'blender':blender, 'coverage':catalog['coverage'],
                'private_models_and_settings_preserved':True,
                'terrain_road_and_shoulders_preserved':True,
                'source_fingerprints':{str(p.relative_to(ROOT)).replace('\\', '/'):
                                       hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                                       for p in [ROOT/'godot/scripts/circuit_environment.gd',
                                                 ROOT/'godot/scripts/circuit.gd',
                                                 ROOT/'godot/tests/circuit_environment_check.gd',
                                                 Path(__file__), ROOT/'tools/blender/build_circuit_environment.py']}}
    (ROOT/'reports/AMBIENTE_CIRCUITO_VERIFICA.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in evidence.items() if k not in ['source_fingerprints','godot','blender','coverage']}, indent=2))


if __name__ == '__main__':
    main()
