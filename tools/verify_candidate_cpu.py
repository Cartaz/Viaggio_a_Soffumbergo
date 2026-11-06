"""Sequential Windows data/physics checks; never launches a renderer or promotes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    parser = argparse.ArgumentParser()
    for name in ['draft', 'runtime-identity', 'generation-journal', 'reentry-candidates', 'reentry-review', 'background-log']:
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--attempt', default='v1'); args = parser.parse_args()
    if not re.fullmatch('v[1-9][0-9]*', args.attempt): raise ValueError('Use a fresh versioned attempt')
    if args.background_log.exists(): raise RuntimeError('Preserve previous pipeline log')
    sys.stdout = args.background_log.open('x', buffering=1); sys.stderr = sys.stdout
    draft = args.draft.resolve(); pack = read(draft/'candidate_packaging_report.json')
    identity = read(args.runtime_identity); build = pack['build_id']
    assert re.fullmatch('[0-9a-f]{12}', build) and pack['packaged'] and identity['build_id'] == build
    assert sha(draft/'circuit_driving_world.json') == pack['world_sha256'] == identity['world_sha256']
    assert sha(draft/'circuit_itinerary.json') == pack['itinerary_sha256'] == identity['itinerary_sha256']
    assert all(sha(path) == expected for path, expected in identity['source_sha256'].items())
    binary = Path(pack['archive'])/'Windows/SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe'
    assert sha(binary) == pack['game_binary_sha256']
    manifest = read(read(draft/'import_report.json')['manifest'])
    assert read(args.reentry_candidates)['build_id'] == read(args.reentry_review)['build_id'] == build
    assert any(c['id'] == 'costalunga_cianal_run' for c in manifest['roadside_structures']['config']['controls'])
    status = draft/('cpu_verification_pipeline_'+args.attempt+'.json')
    if status.exists(): raise RuntimeError('Preserve previous native CPU pipeline')
    state = {'build_id': build, 'attempt': args.attempt, 'started_unix': time.time(), 'status': 'starting',
        'windows_binary_sha256': pack['game_binary_sha256'], 'runtime_identity_sha256': sha(args.runtime_identity),
        'stages': [], 'rendering_requested': False, 'rendered_checks_completed': False,
        'promoted': False, 'complete_objective_reached': False}
    def save(): status.write_text(json.dumps(state, indent=2))
    save()
    def run(name, script, extra, report, passed):
        if report.exists(): raise RuntimeError('Preserve previous stage evidence '+str(report))
        state.update(status=name, stage_started_unix=time.time()); save()
        command = [sys.executable, str(ROOT/'tools'/script), *map(str, extra)]
        child = subprocess.Popen(command, cwd=ROOT, stdout=sys.stdout, stderr=sys.stderr, creationflags=subprocess.CREATE_NO_WINDOW)
        state['stage_wrapper_pid'] = child.pid; save(); code = child.wait()
        if code != 0: raise RuntimeError(name+' verifier exited '+str(code))
        if not report.exists() or report.stat().st_mtime < state['stage_started_unix']: raise RuntimeError(name+' has no fresh final report')
        result = read(report)
        if not passed(result): raise RuntimeError(name+' did not pass the requested scope')
        state['stages'].append({'name': name, 'report': str(report), 'report_sha256': sha(report),
            'passed': True, 'ended_unix': time.time()})
        state.pop('stage_wrapper_pid', None); save()
    try:
        review = draft/('offline_shader_review_'+args.attempt+'.json')
        run('offline_material_compile_review', 'review_candidate_cook.py', ['--draft', draft, '--output', review], review, lambda r: r['passed'])
        run_id = build+'_cpu_pcg_windows_'+args.attempt
        run('windows_vegetation_census', 'run_pcg_runtime_census.py', ['--draft', draft, '--runtime-identity', args.runtime_identity,
            '--generation-journal', args.generation_journal, '--run-id', run_id, '--packaged'],
            ROOT/'results/vegetation_census'/run_id/'report.json', lambda r: r['passed'] and r['packaged'] and not r['rendering'])
        suffix = '' if args.attempt == 'v1' else '_'+args.attempt
        pipeline = draft/('candidate_verification_pipeline'+suffix+'.json')
        run('windows_surface_and_full_lap', 'verify_road_candidate.py', ['--draft', draft, '--headless-only', '--attempt', args.attempt,
            '--background-log', draft/('cpu_surface_lap_'+args.attempt+'.log')], pipeline,
            lambda r: r['status'] == 'native_headless_pipeline_finished' and not r['rendered_checks_requested'])
        run_id = build+'_cpu_polisportivo_'+args.attempt
        run('windows_meadow_reentry', 'run_reentry_check.py', ['--draft', draft, '--candidates', args.reentry_candidates,
            '--streetview-review', args.reentry_review, '--station', '2430', '--run-id', run_id, '--pulse',
            '--out-seconds', '5', '--reverse-seconds', '4.7', '--pulse-brake', '.18', '--allow-geometric-diagnostic'],
            ROOT/'results/reentry_checks'/run_id/'report.json', lambda r: r['passed'] and r['RHI'] == 'Null' and not r['rendering'])
        run_id = build+'_cpu_cianal_'+args.attempt
        run('windows_cianal_contact', 'run_guardrail_check.py', ['--draft', draft, '--packaged', '--control',
            'costalunga_cianal_run', '--run-id', run_id], ROOT/'results/guardrail_checks'/run_id/'report.json',
            lambda r: r['passed'] and r['RHI'] == 'Null' and not r['rendering'])
        assert sha(binary) == pack['game_binary_sha256']
        state.update(status='native_cpu_pipeline_finished', native_cpu_checks_passed=True,
            ended_unix=time.time(), scope='Exact exported Windows data and physics checks. No rendered pixels, manual controls, '
                'GPU stability, representative 4K60 performance or complete artistic/anthropic acceptance.')
        save(); print(json.dumps(state, indent=2))
    except BaseException as error:
        state.update(status='failed', error=repr(error), ended_unix=time.time()); save(); raise


if __name__ == '__main__': main()
