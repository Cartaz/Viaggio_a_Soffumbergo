"""Read back saved drainage assets in a separate NullRHI process."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--draft', type=Path, required=True)
    parser.add_argument('--attempt', default='v1'); args = parser.parse_args()
    if not re.fullmatch('v[1-9][0-9]*', args.attempt): raise ValueError('Use a fresh versioned attempt')
    draft = args.draft.resolve(); prepared = json.loads((draft/'structure_preparation.json').read_text())
    state_path = draft/('drainage_asset_worker_'+args.attempt+'.json')
    report_path = draft/('drainage_asset_audit_'+args.attempt+'.json')
    if state_path.exists() or report_path.exists(): raise RuntimeError('Preserve previous audit evidence')
    command = ['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe',
        str(ROOT/'Unreal/SoffumbergoLab.uproject'), '-unattended', '-nosplash', '-nosound', '-nullrhi',
        '-ExecutePythonScript='+str(ROOT/'tools/audit_drainage_assets.py').replace('\\', '/'),
        '-abslog='+str(draft/('drainage_asset_engine_'+args.attempt+'.log')).replace('\\', '/')]
    env = os.environ.copy(); env['SOFFUMBERGO_DRAINAGE_MANIFEST'] = prepared['manifest']
    env['SOFFUMBERGO_DRAINAGE_AUDIT_OUTPUT'] = str(report_path)
    state = {'build_id': prepared['build_id'], 'started_unix': time.time(), 'command': command, 'passed': False}
    with (draft/('drainage_asset_console_'+args.attempt+'.log')).open('x') as stream:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW)
        state['native_pid'] = process.pid; state_path.write_text(json.dumps(state, indent=2))
        print('DRAINAGE_ASSET_AUDIT_PID '+str(process.pid), flush=True); code = process.wait()
    state.update(native_exit_code=code, ended_unix=time.time())
    if report_path.exists() and report_path.stat().st_mtime >= state['started_unix']:
        report = json.loads(report_path.read_text()); state['passed'] = code == 0 and report['passed']
        if report.get('error'): state['error'] = report['error']
    state_path.write_text(json.dumps(state, indent=2)); print(json.dumps(state, indent=2))
    if not state['passed']: raise SystemExit(1)


if __name__ == '__main__': main()
