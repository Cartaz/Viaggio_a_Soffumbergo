"""Run the native drainage authoring script to real completion, without drawing."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--draft', type=Path, required=True)
    args = parser.parse_args(); draft = args.draft.resolve()
    prepared = json.loads((draft/'structure_preparation.json').read_text())
    state_path = draft/'drainage_worker.json'
    if state_path.exists(): raise RuntimeError('Preserve previous worker evidence')
    command = ['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe',
        str(ROOT/'Unreal/SoffumbergoLab.uproject'), '-unattended', '-nosplash', '-nosound', '-nullrhi',
        '-ExecutePythonScript='+str(ROOT/'tools/import_drainage_surface.py').replace('\\', '/'),
        '-abslog='+str(draft/'drainage_engine.log').replace('\\', '/')]
    env = os.environ.copy(); env['SOFFUMBERGO_DRAINAGE_MANIFEST'] = prepared['manifest']
    state = {'build_id': prepared['build_id'], 'started_unix': time.time(), 'command': command,
        'rendering': False, 'passed': False}
    with (draft/'drainage_console.log').open('x') as stream:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW)
        state['native_pid'] = process.pid; state_path.write_text(json.dumps(state, indent=2))
        print('DRAINAGE_NATIVE_PID '+str(process.pid), flush=True); code = process.wait()
    state.update(native_exit_code=code, ended_unix=time.time())
    journal = draft/'drainage_native_import.json'
    if journal.exists() and journal.stat().st_mtime >= state['started_unix']:
        data = json.loads(journal.read_text()); state['journal'] = str(journal)
        state['passed'] = code == 0 and data['all_imported'] and not data.get('error') and data['protected_files_unchanged']
        if data.get('error'): state['error'] = data['error']
    state_path.write_text(json.dumps(state, indent=2)); print(json.dumps(state, indent=2))
    if not state['passed']: raise SystemExit(1)


if __name__ == '__main__': main()
