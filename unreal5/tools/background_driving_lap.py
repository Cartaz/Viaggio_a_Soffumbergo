"""One-shot long test worker with persistent logs, launched outside the tool tree.

This is an ordinary local Windows process, not a recurring or scheduled task.
The normal driving-lap verifier still owns all native checks and acceptance.
"""
import argparse
import json
from pathlib import Path
import re
import runpy
import sys
import time
import traceback

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--max-fps',type=float);args=p.parse_args()
if not re.fullmatch('[a-z0-9_]+',args.run_id):p.error('Use a unique simple test name')
state=root/'results'/(args.run_id+'_worker.json')
if state.exists():raise RuntimeError('Preserve previous worker state')
started=time.time()
def save(status,**extra):
    state.write_text(json.dumps({'run_id':args.run_id,'started_unix':started,'status':status,**extra},indent=2))
with (root/'results'/(args.run_id+'_stdout.log')).open('w',buffering=1) as output, \
     (root/'results'/(args.run_id+'_stderr.log')).open('w',buffering=1) as errors:
    sys.stdout=output;sys.stderr=errors
    save('running')
    sys.argv=['run_driving_lap.py','--packaged','--render','--run-id',args.run_id,'--timeout','10800']
    if args.max_fps is not None:sys.argv+=['--max-fps',str(args.max_fps)]
    try:
        runpy.run_path(str(root/'tools/run_driving_lap.py'),run_name='__main__')
    except BaseException as error:
        traceback.print_exc();save('worker_failed',ended_unix=time.time(),error=repr(error))
        raise
    else:save('verifier_finished',ended_unix=time.time())
