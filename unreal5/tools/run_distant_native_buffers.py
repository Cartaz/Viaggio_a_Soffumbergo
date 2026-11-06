"""Sequential NullRHI native buffer audit with observable process lifetime."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--draft',type=Path,required=True);args=p.parse_args()
    draft=args.draft.resolve();prep=json.loads((draft/'structure_preparation.json').read_text())
    path=draft/'distant_buffer_worker.json'
    if path.exists():raise RuntimeError('Preserve previous worker')
    command=['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe',str(ROOT/'Unreal/SoffumbergoLab.uproject'),
        '-nullrhi','-unattended','-nosplash','-nosound',
        '-ExecutePythonScript='+str(ROOT/'tools/audit_distant_native_buffers.py').replace('\\','/'),
        '-abslog='+str(draft/'distant_buffer_engine.log').replace('\\','/')]
    env=os.environ.copy();env['SOFFUMBERGO_DISTANT_BUFFER_MANIFEST']=prep['manifest']
    state={'build_id':prep['build_id'],'started_unix':time.time(),'command':command,'passed':False}
    with (draft/'distant_buffer_console.log').open('x') as stream:
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        state['native_pid']=process.pid;path.write_text(json.dumps(state,indent=2));print('DISTANT_BUFFER_PID '+str(process.pid),flush=True);code=process.wait()
    state.update(native_exit_code=code,ended_unix=time.time())
    result=draft/'distant_native_buffers.json'
    if result.exists() and result.stat().st_mtime>=state['started_unix']:
        report=json.loads(result.read_text());state['passed']=code==0 and report['passed'] and report.get('protected_files_unchanged')
        if report.get('error'):state['error']=report['error']
    path.write_text(json.dumps(state,indent=2));print(json.dumps(state,indent=2))
    if not state['passed']:raise SystemExit(1)


if __name__=='__main__':main()
