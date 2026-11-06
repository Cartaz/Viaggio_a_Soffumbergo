"""One-shot native import with explicit process/final-result evidence."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--draft',type=Path,required=True)
    p.add_argument('--background-log',type=Path,required=True)
    p.add_argument('--attempt',default='v1');p.add_argument('--resume-journal',type=Path)
    args=p.parse_args()
    if not args.attempt.replace('_','').isalnum():raise ValueError('Invalid attempt')
    sys.stdout=args.background_log.open('x',buffering=1);sys.stderr=sys.stdout
    draft=args.draft.resolve();prepared=json.loads((draft/'structure_preparation.json').read_text())
    audit=json.loads((draft/'structure_geometry_audit.json').read_text())
    if not audit['passed'] or audit['build_id']!=prepared['build_id']:raise RuntimeError('Matching geometry audit required')
    result_path=draft/('native_import_worker'+('' if args.attempt=='v1' else '_'+args.attempt)+'.json')
    if result_path.exists():raise RuntimeError('Preserve earlier import run')
    engine=Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')
    command=[str(engine),str(ROOT/'Unreal/SoffumbergoLab.uproject'),'-unattended','-nosplash','-nosound','-nullrhi',
        '-ExecutePythonScript='+str(ROOT/'tools/import_shoulder_repair.py').replace('\\','/'),
        '-abslog='+str(draft/('shoulder_import_engine_'+args.attempt+'.log')).replace('\\','/')]
    env=os.environ.copy();env['SOFFUMBERGO_SHOULDER_MANIFEST']=prepared['manifest']
    env['SOFFUMBERGO_SHOULDER_ATTEMPT']=args.attempt
    if args.resume_journal:env['SOFFUMBERGO_SHOULDER_RESUME_JOURNAL']=str(args.resume_journal.resolve())
    started=time.time();state={'build_id':prepared['build_id'],'started_unix':started,'command':command,'passed':False}
    with (draft/('shoulder_import_console_'+args.attempt+'.log')).open('x') as output:
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        state['native_pid']=process.pid;result_path.write_text(json.dumps(state,indent=2))
        process.wait(timeout=1800)
    report=draft/'import_report.json'
    state.update(native_exit_code=process.returncode,ended_unix=time.time())
    if process.returncode==0 and report.exists() and report.stat().st_mtime>=started:
        data=json.loads(report.read_text());state['passed']=data['all_imported'] and data['build_id']==prepared['build_id']
    result_path.write_text(json.dumps(state,indent=2));print(json.dumps(state,indent=2))
    if not state['passed']:raise SystemExit(1)


if __name__=='__main__':main()
