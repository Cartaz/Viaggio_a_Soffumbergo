"""Observable native PCG worker; observation expiry never kills or restarts Unreal."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(); p.add_argument('--draft', type=Path, required=True)
    p.add_argument('--attempt', required=True); p.add_argument('--resume', type=Path)
    p.add_argument('--diagnostic-tile-limit', type=int, default=0); args = p.parse_args()
    if not args.attempt.replace('_', '').isalnum(): raise ValueError('Unsafe attempt')
    draft = args.draft.resolve(); prepared = json.loads((draft/'structure_preparation.json').read_text())
    state_path = draft/('world_pcg_worker_'+args.attempt+'.json')
    if state_path.exists(): raise RuntimeError('Preserve previous worker')
    log_path = draft/('world_pcg_engine_'+args.attempt+'.log'); console_path = draft/('world_pcg_console_'+args.attempt+'.log')
    command = ['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe',
        str(ROOT/'Unreal/SoffumbergoLab.uproject'), '-unattended', '-nosplash', '-nosound', '-nullrhi',
        '-ExecutePythonScript='+str(ROOT/'tools/import_world_vegetation.py').replace('\\', '/'), '-abslog='+str(log_path).replace('\\', '/')]
    env = os.environ.copy(); env['SOFFUMBERGO_WORLD_PCG_MANIFEST'] = prepared['manifest']
    env['SOFFUMBERGO_WORLD_PCG_ATTEMPT'] = args.attempt
    env['SOFFUMBERGO_WORLD_PCG_TILE_LIMIT'] = str(args.diagnostic_tile_limit)
    if args.resume: env['SOFFUMBERGO_WORLD_PCG_RESUME'] = str(args.resume.resolve())
    state = {'build_id': prepared['build_id'], 'command': command, 'started_unix': time.time(),
        'diagnostic_tile_limit': args.diagnostic_tile_limit, 'passed': False, 'resume_journal': env.get('SOFFUMBERGO_WORLD_PCG_RESUME')}
    with console_path.open('x') as output:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        state['native_pid'] = process.pid; state_path.write_text(json.dumps(state, indent=2)); print('WORLD_PCG_NATIVE_PID '+str(process.pid), flush=True)
        code = process.wait()
    state.update(native_exit_code=code, ended_unix=time.time())
    journal_path = draft/('world_pcg_native_'+args.attempt+'.json')
    if journal_path.exists() and journal_path.stat().st_mtime >= state['started_unix']:
        journal = json.loads(journal_path.read_text()); state['journal'] = str(journal_path)
        scope = len(journal['tiles']) >= args.diagnostic_tile_limit and all(t['saved_complete'] for t in journal['tiles'].values()) if args.diagnostic_tile_limit else journal['all_imported']
        state['passed'] = code == 0 and not journal.get('error') and journal.get('protected_files_unchanged') and scope
        state['completed_tiles'] = len([t for t in journal['tiles'].values() if t.get('saved_complete')])
        if journal.get('error'): state['error'] = journal['error']
    state_path.write_text(json.dumps(state, indent=2)); print(json.dumps(state, indent=2))
    if not state['passed']: raise SystemExit(1)


if __name__ == '__main__': main()
