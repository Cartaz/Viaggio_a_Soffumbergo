"""Run reproducible source, real Jolt, rendered road and Blender acceptance gates."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--godot',type=Path,required=True)
    p.add_argument('--blender',type=Path)
    p.add_argument('--capture',action='store_true')
    a=p.parse_args()
    out=ROOT/'build/drive_validation'
    out.mkdir(parents=True,exist_ok=True)
    steps=[]
    report=out/'validation_report.json'
    report.write_text('{"passed":false}\n')

    def run(name,command):
        start=time.monotonic()
        r=subprocess.run([str(s) for s in command],cwd=ROOT,capture_output=True,
                         text=True,encoding='utf-8',errors='replace',timeout=360)
        log=r.stdout+r.stderr
        (out/(name+'.log')).write_text(log,encoding='utf-8')
        errors=bool(re.search(r'(^|\n)(SCRIPT ERROR:|ERROR:|Traceback|WARNING: ObjectDB)',log))
        step={'name':name,'exit_code':r.returncode,'engine_errors':errors,'seconds':round(time.monotonic()-start,3)}
        steps.append(step)
        report.write_text(json.dumps({'passed':False,'steps':steps},indent=2)+'\n')
        print(json.dumps(step),flush=True)
        if r.returncode or errors:
            raise RuntimeError('Validation failed: '+name)

    run('python',[sys.executable,'tools/check_project.py'])
    run('yaris_asset',[sys.executable,'tools/check_yaris_asset.py'])
    files=sorted(str(p.relative_to(ROOT)) for p in (ROOT/'godot').rglob('*.gd'))
    for tool,flags in [('gdparse',[]),('gdformat',['--check']),('gdlint',[])]:
        program=shutil.which(tool) or Path(sys.executable).parent/(tool+('.exe' if sys.platform=='win32' else ''))
        run(tool,[program]+flags+files)
    original=(ROOT/'build/circuit/manifest.json').read_bytes()
    run('generate',[sys.executable,'tools/build_drive_pilot.py'])
    generated={n:hashlib.sha256((ROOT/'build/circuit'/n).read_bytes()).hexdigest() for n in ['pilot_manifest.json','pilot_road.json']}
    run('regenerate',[sys.executable,'tools/build_drive_pilot.py'])
    for n,h in generated.items():
        if hashlib.sha256((ROOT/'build/circuit'/n).read_bytes()).hexdigest()!=h:
            raise ValueError('Non-deterministic trial generation')
    if (ROOT/'build/circuit/manifest.json').read_bytes()!=original:
        raise ValueError('Original circuit manifest changed')
    engine=[a.godot.resolve(),'--path',ROOT]
    run('import',engine+['--headless','--editor','--quit'])
    for name,script in [('reference','reference_checks'),('lab','lab_yaris_check'),('valle','valle_check')]:
        run(name,engine+['--headless','--fixed-fps','120','--script','godot/tests/'+script+'.gd'])
    for hz in [60,120]:
        run('performance_'+str(hz),engine+['--headless','--fixed-fps',str(hz),'--script',
            'godot/tests/yaris_performance_check.gd','--','--hz='+str(hz),'--output=build/yaris_performance/'+str(hz)])
    runs=[json.loads((ROOT/f'build/yaris_performance/{hz}/report.json').read_text()) for hz in [60,120]]
    for kind in ['stock','rig']:
        if abs(runs[0][kind]['time_0_100_s']-runs[1][kind]['time_0_100_s'])>.5:
            raise ValueError('Excessive 60/120Hz acceleration variation')
    run('drive_headless',engine+['--headless','--fixed-fps','120','--script','godot/tests/drive_pilot_check.gd'])
    if a.capture:
        run('drive_render',engine+['--fixed-fps','120','--script','godot/tests/drive_pilot_check.gd','--','--capture'])
    if a.blender:
        run('blender',[a.blender.resolve(),'--background','--factory-startup','--python','tools/blender/build_drive_pilot.py'])
    report.write_text(json.dumps({'passed':True,'steps':steps,'deterministic_files':generated,
        'original_circuit_sha256':hashlib.sha256(original).hexdigest()},indent=2)+'\n')


if __name__=='__main__':
    main()
