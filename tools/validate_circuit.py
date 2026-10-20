"""End-to-end corridor gate with deterministic generation, real source and engine probes."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from register_dtm import sha256_file

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--godot',type=Path,required=True)
    parser.add_argument('--blender',type=Path)
    parser.add_argument('--input-dir',type=Path)
    parser.add_argument('--capture',action='store_true')
    args = parser.parse_args()
    folder = ROOT/'build/circuit_validation'
    folder.mkdir(parents=True,exist_ok=True)
    (ROOT/'build/.gdignore').touch()
    steps = []
    report_path = folder/'validation_report.json'
    report_path.write_text('{"passed":false}\n',encoding='utf-8')

    def run(name,command):
        started = time.monotonic()
        try:
            result = subprocess.run([str(v) for v in command],cwd=ROOT,capture_output=True,
                                    text=True,encoding='utf-8',errors='replace',timeout=180)
            log = result.stdout+result.stderr
        except subprocess.TimeoutExpired as exc:
            report_path.write_text(json.dumps({'passed':False,'steps':steps,'timeout':name})+'\n',encoding='utf-8')
            raise RuntimeError('Validation step timed out: '+name) from exc
        (folder/(name+'.log')).write_text(log,encoding='utf-8')
        errors = bool(re.search(r'(^|\n)(SCRIPT ERROR:|ERROR:|Traceback|WARNING: ObjectDB)',log))
        step = {'name':name,'exit_code':result.returncode,'seconds':round(time.monotonic()-started,3),'engine_errors':errors}
        steps.append(step)
        report_path.write_text(json.dumps({'passed':False,'steps':steps},indent=2)+'\n',encoding='utf-8')
        print(json.dumps(step),flush=True)
        if result.returncode or errors:
            raise RuntimeError('Validation failed: '+name+'; inspect '+str(folder/(name+'.log')))

    run('python',[sys.executable,'tools/check_project.py'])
    run('yaris_regression',[sys.executable,'tools/check_yaris_asset.py'])
    gd_files = sorted(str(p.relative_to(ROOT)) for p in (ROOT/'godot').rglob('*.gd'))
    for name,extra in [('gdparse',[]),('gdformat',['--check']),('gdlint',[])]:
        program = shutil.which(name) or Path(sys.executable).parent/(name+('.exe' if sys.platform=='win32' else ''))
        run(name,[program]+extra+gd_files)
    if args.input_dir:
        command = [sys.executable,'tools/build_circuit_3d.py','--input-dir',args.input_dir.resolve()]
        run('generate',command)
        digest = sha256_file(ROOT/'build/circuit/manifest.json')
        run('regenerate',command)
        if sha256_file(ROOT/'build/circuit/manifest.json') != digest:
            raise RuntimeError('Corridor generation was not deterministic')
    geometry = [sys.executable,'tools/check_circuit_3d.py','build/circuit/manifest.json']
    if args.input_dir:
        geometry += ['--input-dir',args.input_dir.resolve()]
    run('geometry',geometry)
    godot = [args.godot.resolve(),'--path',ROOT]
    run('godot_import',godot+['--headless','--editor','--quit'])
    for name,script in [('reference','reference_checks'),('mesh','circuit_mesh_check'),('valle','valle_check')]:
        run('godot_'+name,godot+['--headless','--script',f'res://godot/tests/{script}.gd',
                                 '--','--output=build/circuit_validation/'+name])
    test = godot+['--script','res://godot/tests/circuit_check.gd']
    run('godot_headless',test+['--headless','--','--output=build/circuit_validation/headless'])
    run('godot_missing',test+['--headless','--','--circuit-data=build/absent-circuit-test.json',
                             '--expect-missing','--output=build/circuit_validation/missing'])
    if args.capture:
        run('godot_render',test+['--','--capture','--output=build/circuit_validation/render'])
    if args.blender:
        run('blender',[args.blender.resolve(),'--background','--factory-startup',
                       '--python','tools/blender/build_circuit.py','--','--overwrite'])
    report = {'passed':True,'steps':steps,'manifest_sha256':sha256_file(ROOT/'build/circuit/manifest.json')}
    report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()
