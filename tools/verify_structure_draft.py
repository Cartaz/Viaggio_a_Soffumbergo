"""One-shot verification of an imported structure derivative, without promotion."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
import _winapi

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--draft',type=Path,required=True)
    p.add_argument('--wait-render-pid',type=int);p.add_argument('--background-log',type=Path,required=True)
    p.add_argument('--guardrail-report',type=Path)
    p.add_argument('--editor-only',action='store_true',help='Stop after the full native Editor surface and driven lap, without export')
    args=p.parse_args();sys.stdout=args.background_log.open('w',buffering=1);sys.stderr=sys.stdout
    draft=args.draft.resolve();prepared=json.loads((draft/'structure_preparation.json').read_text())
    build=prepared['build_id'];manifest=Path(prepared['manifest'])
    if prepared.get('diagnostic_only'):raise RuntimeError('Local diagnostics cannot enter whole-territory verification')
    imported=json.loads((draft/'import_report.json').read_text());audit=json.loads((draft/'structure_geometry_audit.json').read_text())
    if not imported['all_imported'] or not audit['passed'] or imported['build_id']!=build or audit['build_id']!=build:
        raise RuntimeError('Matching native import and geometry audit are required')
    state_path=draft/'structure_verification_pipeline.json'
    if state_path.exists():raise RuntimeError('Preserve earlier verification pipeline')
    state={'build_id':build,'status':'starting','started_unix':time.time(),'stages':[],
           'promoted':False,'visual_and_remaining_structural_review_required':True,'wait_render_pid':args.wait_render_pid}
    def save():state_path.write_text(json.dumps(state,indent=2))
    save()
    handle=None
    if args.wait_render_pid:
        try:handle=_winapi.OpenProcess(0x00100000,False,args.wait_render_pid)
        except OSError:pass
    if args.guardrail_report:
        contact=json.loads(args.guardrail_report.read_text())
        if not contact['passed'] or contact['build_id']!=build:raise RuntimeError('Physical guardrail prerequisite failed')
        state['guardrail_prerequisite']=str(args.guardrail_report.resolve());save()
    def run(name,script,arguments,report=None,key='passed'):
        state['status']=name;save();started=time.time()
        result=subprocess.run([sys.executable,str(ROOT/'tools'/script),*arguments],cwd=ROOT,
            stdout=sys.stdout,stderr=sys.stderr,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:raise RuntimeError(name+' failed; inspect preserved native evidence')
        if report is not None:
            data=json.loads(report.read_text(encoding='utf-8-sig'))
            if report.stat().st_mtime<started or not data.get(key):raise RuntimeError(name+' has no fresh accepted report')
        state['stages'].append({'name':name,'report':str(report) if report else None,'ended_unix':time.time()});save()
    surface_id='structures_'+build+'_surface_editor_v1';lap_id='structures_'+build+'_full_editor_v1'
    surface=ROOT/'results/road_draft_checks'/surface_id/'report.json'
    lap=ROOT/'results/road_draft_checks'/lap_id/'report.json'
    cases=ROOT/'results'/('reentry_candidates_'+build+'.json')
    try:
        run('editor_surface','run_draft_road_check.py',['--draft',str(draft),'--run-id',surface_id,'--mode','survey'],surface)
        run('editor_full_lap','run_draft_road_check.py',['--draft',str(draft),'--run-id',lap_id,'--mode','lap','--timeout','1800'],lap,'full_lap_passed')
        if args.editor_only:
            state['status']='native_editor_checks_finished';state['ended_unix']=time.time();save()
            return
        run('windows_export','package_road_draft.py',['--draft',str(draft),'--lap-report',str(lap),'--surface-report',str(surface)],
            draft/'candidate_packaging_report.json','packaged')
        guard_id='candidate_'+build+'_guardrail_windows_v1'
        run('windows_guardrail_contact','run_guardrail_check.py',['--draft',str(draft),'--run-id',guard_id,'--packaged'],
            ROOT/'results/guardrail_checks'/guard_id/'report.json')
        run('access_resampling','prepare_reentry_checks.py',['--manifest',str(manifest),'--itinerary',str(draft/'circuit_itinerary.json'),'--output',str(cases)])
        reentry_id='candidate_'+build+'_meadow_headless_pulse_v2'
        run('windows_reentry_headless','run_reentry_check.py',['--draft',str(draft),'--candidates',str(cases),'--run-id',reentry_id,
            '--pulse','--out-seconds','5','--reverse-seconds','4.7','--pulse-brake','.18'],
            ROOT/'results/reentry_checks'/reentry_id/'report.json')
        state['status']='waiting_for_existing_renderer';save()
        if handle is not None:
            while _winapi.WaitForSingleObject(handle,30000)==258:pass
            _winapi.CloseHandle(handle);handle=None
        # The previous renderer's exact process handle is terminal. The child
        # pipeline performs Windows surface/lap, default-map input and full RHI.
        run('windows_native_pipeline','verify_road_candidate.py',['--draft',str(draft),
            '--background-log',str(draft/'windows_native_pipeline.log')])
        completed=json.loads((draft/'candidate_verification_pipeline.json').read_text())
        if completed['status']!='native_pipeline_finished':raise RuntimeError('Windows native pipeline did not finish')
        reentry_id='candidate_'+build+'_meadow_windows_4k60_v1'
        run('windows_reentry_rendered','run_reentry_check.py',['--draft',str(draft),'--candidates',str(cases),'--run-id',reentry_id,
            '--pulse','--out-seconds','5','--reverse-seconds','4.7','--pulse-brake','.18','--render','--max-fps','60'],
            ROOT/'results/reentry_checks'/reentry_id/'report.json')
        state['status']='native_checks_finished';state['ended_unix']=time.time();save()
    except BaseException as error:
        state['status']='failed';state['error']=repr(error);state['ended_unix']=time.time();save()
        traceback.print_exc();raise
    finally:
        if handle is not None:_winapi.CloseHandle(handle)


if __name__=='__main__':main()
