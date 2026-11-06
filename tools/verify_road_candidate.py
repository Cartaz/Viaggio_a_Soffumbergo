"""One-shot, gated native checks for a separate exported road candidate.

Headless checks run first. Rendered checks wait for the explicitly identified
existing renderer to exit, so there are no competing Unreal renderers. Every
stage uses existing strict verifiers and stops on failure. No build is promoted
and no visual or structural requirement is declared complete by this worker.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import _winapi

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--draft',type=Path,required=True)
    p.add_argument('--wait-render-pid',type=int);p.add_argument('--background-log',type=Path,required=True)
    p.add_argument('--attempt',default='v1',help='Fresh evidence namespace; earlier attempts are retained')
    p.add_argument('--include-structure-reentry',action='store_true')
    p.add_argument('--reentry-station',type=float,default=2430,help='Explicit station from the current, resampled access set')
    p.add_argument('--skip-long-render',action='store_true',help='Run complete headless checks and local rendered controls, but defer the long rendered lap while structural review is open')
    p.add_argument('--headless-only',action='store_true',help='Run only complete Windows surface/physics checks; never start a renderer')
    args=p.parse_args();sys.stdout=args.background_log.open('w',buffering=1);sys.stderr=sys.stdout
    if args.headless_only and args.include_structure_reentry:raise ValueError('Rendered reentry cannot run in headless-only mode')
    if not re.fullmatch('v[1-9][0-9]*',args.attempt):raise ValueError('Attempt must be v1, v2, ...')
    draft=args.draft.resolve()
    preparation=draft/'structure_preparation.json'
    if preparation.exists() and json.loads(preparation.read_text()).get('diagnostic_only'):
        raise RuntimeError('A local diagnostic cannot enter whole-territory acceptance')
    pack=json.loads((draft/'candidate_packaging_report.json').read_text())
    if not pack['packaged']:raise RuntimeError('No completed candidate package')
    build=pack['build_id']
    if not re.fullmatch('[0-9a-f]{12}',build):raise ValueError('Invalid candidate id')
    status=draft/('candidate_verification_pipeline'+('' if args.attempt=='v1' else '_'+args.attempt)+'.json')
    if status.exists():raise RuntimeError('Preserve prior pipeline; inspect its recorded result')
    state={'build_id':build,'started_unix':time.time(),'status':'starting','stages':[],
           'attempt':args.attempt,
           'long_rendered_lap_requested':not (args.skip_long_render or args.headless_only),
           'rendered_checks_requested':not args.headless_only,
           'published':False,'promoted':False,'needs_visual_and_structural_review':True,
           'wait_render_pid':args.wait_render_pid}
    def save():status.write_text(json.dumps(state,indent=2))
    save();wait_handle=None
    if args.wait_render_pid:
        try:wait_handle=_winapi.OpenProcess(0x00100000,False,args.wait_render_pid)
        except OSError:
            # A missing handle is terminal for this specific old process. No
            # observation deadline is used to terminate or restart any renderer.
            state['old_renderer_handle_already_missing']=True
    world=draft/'circuit_driving_world.json';itinerary=draft/'circuit_itinerary.json'
    package=Path(pack['archive'])/'Windows'
    expected=pack['world_sha256']
    if hashlib.sha256(world.read_bytes()).hexdigest()!=expected:raise RuntimeError('Packaged source world changed')
    if hashlib.sha256(itinerary.read_bytes()).hexdigest()!=pack['itinerary_sha256']:raise RuntimeError('Packaged itinerary changed')
    binary=package/'SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe'
    if hashlib.sha256(binary.read_bytes()).hexdigest()!=pack['game_binary_sha256']:raise RuntimeError('Packaged game binary changed')
    common=['--packaged','--package-root',str(package),'--world',str(world)]
    def run(stage,script,extra,report,key):
        state['status']=stage;save()
        # Give each retry distinct native outputs as well as its own pipeline state.
        if args.attempt!='v1':
            extra=[item[:-3]+'_'+args.attempt if item.endswith('_v1') else item for item in extra]
            report=Path(str(report).replace('_v1', '_'+args.attempt))
            if script=='run_structure_gallery.py':
                extra+=['--attempt',args.attempt]
                report=ROOT/'results/structure_gallery'/build/args.attempt/'report.json'
        command=[sys.executable,str(ROOT/'tools'/script),*extra]
        started=time.time()
        result=subprocess.run(command,cwd=ROOT,stdout=sys.stdout,stderr=sys.stderr,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:raise RuntimeError(stage+' verifier failed; inspect retained native evidence')
        data=json.loads(report.read_text(encoding='utf-8-sig'))
        if report.stat().st_mtime<started or not data.get(key):raise RuntimeError(stage+' has no fresh accepted report')
        state['stages'].append({'name':stage,'report':str(report),'passed':True,'ended_unix':time.time()});save()
    try:
        run('surface','run_road_survey.py',common+['--import-report',str(draft/'import_report.json'),'--run-id','candidate_'+build+'_surface_v1'],
            ROOT/'results/road_surface_packaged'/('candidate_'+build+'_surface_v1')/'run_manifest.json','passed')
        run('headless_full_lap','run_driving_lap.py',common+['--itinerary',str(itinerary),'--run-id','candidate_'+build+'_full_windows_v1','--timeout','1800'],
            ROOT/'results/driving_laps'/('candidate_'+build+'_full_windows_v1')/'report.json','full_lap_passed')
        if args.headless_only:
            state.update(status='native_headless_pipeline_finished',long_rendered_lap_completed=False,
                rendered_checks_completed=False,ended_unix=time.time())
            save();print(json.dumps(state,indent=2));return
        state['status']='waiting_for_existing_renderer';save()
        if wait_handle is not None:
            while _winapi.WaitForSingleObject(wait_handle,30000)==258:pass
            _winapi.CloseHandle(wait_handle);wait_handle=None
        run('bootstrap_default_map_controls_4k','run_input_checks.py',common+['--import-report',str(draft/'import_report.json'),
            '--bootstrap','--default-map','--run-id','candidate_'+build+'_bootstrap_default_4k_v1'],
            ROOT/'results/input_checks'/('candidate_'+build+'_bootstrap_default_4k_v1')/'report.json','passed')
        if (draft/'structure_preparation.json').exists():
            contact_run='candidate_'+build+'_guardrail_windows_4k_v1'
            run('guardrail_contact_4k','run_guardrail_check.py',['--draft',str(draft),'--packaged','--render','--run-id',contact_run],
                ROOT/'results/guardrail_checks'/contact_run/'report.json','passed')
            run('roadside_gallery_4k','run_structure_gallery.py',['--draft',str(draft)],
                ROOT/'results/structure_gallery'/build/'v1/report.json','passed')
        if not args.skip_long_render:
            run('rendered_full_lap_4k_60','run_driving_lap.py',common+['--itinerary',str(itinerary),'--render','--max-fps','60',
                '--run-id','candidate_'+build+'_full_windows_4k60_v1','--timeout','10800'],
                ROOT/'results/driving_laps'/('candidate_'+build+'_full_windows_4k60_v1')/'report.json','full_lap_passed')
        if args.include_structure_reentry:
            reentry_run='candidate_'+build+'_meadow_windows_4k60_v1'
            run('structure_reentry_4k_60','run_reentry_check.py',['--draft',str(draft),
                '--candidates',str(ROOT/'results'/('reentry_candidates_'+build+'.json')),
                '--station',str(args.reentry_station),
                '--run-id',reentry_run,'--pulse','--out-seconds','5','--reverse-seconds','4.7',
                '--pulse-brake','.18','--render','--max-fps','60'],
                ROOT/'results/reentry_checks'/reentry_run/'report.json','passed')
        state['status']='native_short_render_pipeline_finished' if args.skip_long_render else 'native_pipeline_finished'
        state['long_rendered_lap_completed']=not args.skip_long_render
        state['ended_unix']=time.time();save()
    except BaseException as error:
        state['status']='failed';state['error']=repr(error);state['ended_unix']=time.time();save();traceback.print_exc();raise
    finally:
        if wait_handle is not None:_winapi.CloseHandle(wait_handle)


if __name__=='__main__':main()
