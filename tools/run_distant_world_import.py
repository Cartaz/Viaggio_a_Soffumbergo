"""Observe a sequential CPU-only native worker through actual termination."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--draft',type=Path,required=True);args=p.parse_args()
    draft=args.draft.resolve();prepared=json.loads((draft/'structure_preparation.json').read_text())
    state_path=draft/'distant_native_worker.json'
    if state_path.exists():raise RuntimeError('Preserve previous worker')
    command=['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe',
        str(ROOT/'Unreal/SoffumbergoLab.uproject'),'-unattended','-nosplash','-nosound','-nullrhi',
        '-ExecutePythonScript='+str(ROOT/'tools/import_distant_world.py').replace('\\','/'),
        '-abslog='+str(draft/'distant_native_engine.log').replace('\\','/')]
    env=os.environ.copy();env['SOFFUMBERGO_DISTANT_MANIFEST']=prepared['manifest']
    state={'build_id':prepared['build_id'],'started_unix':time.time(),'command':command,'passed':False}
    with (draft/'distant_native_console.log').open('x') as out:
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        state['native_pid']=process.pid;state_path.write_text(json.dumps(state,indent=2));print('DISTANT_NATIVE_PID '+str(process.pid),flush=True)
        code=process.wait()
    state.update(native_exit_code=code,ended_unix=time.time());jpath=draft/'distant_native_import.json'
    if jpath.exists() and jpath.stat().st_mtime>=state['started_unix']:
        j=json.loads(jpath.read_text());state['journal']=str(jpath)
        state['passed']=code==0 and j['all_imported'] and not j.get('error') and j['protected_files_unchanged']
        if j.get('error'):state['error']=j['error']
    state_path.write_text(json.dumps(state,indent=2));print(json.dumps(state,indent=2))
    if not state['passed']:raise SystemExit(1)


if __name__=='__main__':main()
