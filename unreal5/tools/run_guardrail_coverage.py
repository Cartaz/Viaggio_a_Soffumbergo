"""Sequential native contact/reverse trials at all six observed rail controls."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--draft',type=Path,required=True)
    parser.add_argument('--attempt',default='v1');parser.add_argument('--packaged',action='store_true')
    parser.add_argument('--background-log',type=Path,required=True);args=parser.parse_args()
    sys.stdout=args.background_log.open('x',encoding='utf-8',buffering=1);sys.stderr=sys.stdout
    if not re.fullmatch('[a-z0-9_]+',args.attempt):raise ValueError('Simple fresh attempt required')
    draft=args.draft.resolve();imported=json.loads((draft/'import_report.json').read_text())
    m=json.loads(Path(imported['manifest']).read_text());build=m['build_id']
    if not imported['all_imported'] or imported['build_id']!=build:raise RuntimeError('Matching native import required')
    out=draft/('guardrail_coverage_'+args.attempt+'.json')
    if out.exists():raise RuntimeError('Preserve earlier coverage evidence')
    controls=m['roadside_structures']['config']['controls']
    report={'build_id':build,'runtime':'Windows' if args.packaged else 'Editor','started_unix':time.time(),
        'passed':False,'controls':[],'scope':'One low-speed ordinary 12 percent pedal contact, push, reverse release and stop per observed local control; no high-speed safety or full-route coverage claim.'}
    def save():out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    save()
    try:
        for control in controls:
            run='coverage_'+build+'_'+control['id']+'_'+args.attempt;started=time.time()
            command=[sys.executable,str(ROOT/'tools/run_guardrail_check.py'),'--draft',str(draft),'--control',control['id'],'--run-id',run]
            if args.packaged:command.append('--packaged')
            result=subprocess.run(command,cwd=ROOT,stdout=sys.stdout,stderr=sys.stderr,creationflags=subprocess.CREATE_NO_WINDOW)
            path=ROOT/'results/guardrail_checks'/run/'report.json'
            native=json.loads(path.read_text()) if path.exists() else {}
            passed=result.returncode==0 and path.stat().st_mtime>=started and native.get('passed') and native.get('build_id')==build
            report['controls'].append({'control':control['id'],'report':str(path),'passed':bool(passed),'exit_code':result.returncode});save()
            if not passed:raise RuntimeError('Native contact check failed: '+control['id'])
        report['passed']=len(report['controls'])==len(controls);report['ended_unix']=time.time();save()
    except BaseException as error:
        report['error']=repr(error);report['ended_unix']=time.time();save();raise


if __name__=='__main__':main()
