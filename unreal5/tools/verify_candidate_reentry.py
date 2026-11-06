"""One-shot rendered reentry after a specific, already-running QA pipeline exits."""
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
    parser=argparse.ArgumentParser()
    parser.add_argument('--draft',type=Path,required=True)
    parser.add_argument('--wait-pipeline-pid',type=int,required=True)
    parser.add_argument('--background-log',type=Path,required=True)
    args=parser.parse_args()
    sys.stdout=args.background_log.open('w',buffering=1);sys.stderr=sys.stdout
    draft=args.draft.resolve()
    pipeline=draft/'candidate_verification_pipeline.json'
    state_path=draft/'candidate_reentry_pipeline.json'
    if state_path.exists():raise RuntimeError('Preserve earlier run and inspect its result')
    build=json.loads(pipeline.read_text())['build_id']
    prerequisite=ROOT/'results/reentry_checks'/('candidate_'+build+'_meadow_headless_pulse_v2')/'report.json'
    headless=json.loads(prerequisite.read_text())
    if not headless['passed'] or headless['world_build_id']!=build:raise RuntimeError('Missing candidate physical access check')
    state={'build_id':build,'status':'waiting_for_native_pipeline','wait_pipeline_pid':args.wait_pipeline_pid,
           'started_unix':time.time(),'promoted':False,'prerequisite':str(prerequisite)}
    def save():state_path.write_text(json.dumps(state,indent=2))
    save()
    try:
        # Retain this exact process object across observations; never restart
        # native work because an observation timeout expired.
        try:handle=_winapi.OpenProcess(0x00100000,False,args.wait_pipeline_pid)
        except OSError:handle=None
        if handle is not None:
            try:
                while _winapi.WaitForSingleObject(handle,30000)==258:pass
            finally:_winapi.CloseHandle(handle)
        completed=json.loads(pipeline.read_text())
        if completed['status']!='native_pipeline_finished' or not all(s['passed'] for s in completed['stages']):
            raise RuntimeError('Earlier native pipeline did not finish successfully; inspect its evidence')
        run='candidate_'+build+'_meadow_windows_4k60_v1'
        command=[sys.executable,str(ROOT/'tools/run_reentry_check.py'),'--draft',str(draft),
                 '--candidates',str(ROOT/'results'/('reentry_candidates_'+build+'.json')),
                 '--run-id',run,'--pulse','--out-seconds','5','--reverse-seconds','4.7',
                 '--pulse-brake','.18','--render','--max-fps','60']
        state['status']='rendered_reentry';state['command']=command;save()
        result=subprocess.run(command,cwd=ROOT,stdout=sys.stdout,stderr=sys.stderr,creationflags=subprocess.CREATE_NO_WINDOW)
        report=ROOT/'results/reentry_checks'/run/'report.json'
        if result.returncode or not json.loads(report.read_text())['passed']:
            raise RuntimeError('Rendered reentry failed; retained native output requires review')
        state['status']='rendered_reentry_passed';state['report']=str(report)
        state['visual_review_still_required']=True;state['ended_unix']=time.time();save()
    except BaseException as error:
        state['status']='failed';state['error']=repr(error);state['ended_unix']=time.time();save()
        traceback.print_exc();raise


if __name__=='__main__':main()
