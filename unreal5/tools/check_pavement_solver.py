"""Analytic plane, shared-boundary and correction-budget regression checks."""
import json
from pathlib import Path
import numpy as np
from road_surface_fairing import fair_pavement

root=Path(__file__).resolve().parents[1]
def chunks(spike=False):
    result=[]
    for left in [0,1]:
        xy=np.array([[left,0],[left+1,0],[left+1,1],[left,1]],float)
        height=2+.2*xy[:,0]-.02*xy[:,1]
        if spike:height+=((xy[:,0]==1)&(xy[:,1]==1))*.4
        result.append({'vertices':np.column_stack([xy[:,0],height,xy[:,1]]),'triangles':np.array([[0,1,2],[0,2,3]])})
    return result
plane=chunks();original=[c['vertices'].copy() for c in plane]
a=fair_pavement(plane,.24,.75)
checks={'analytic_20pct_plane_preserved':all(np.max(np.abs(c['vertices']-v))<1.e-12 for c,v in zip(plane,original))}
spike=chunks(True);b=fair_pavement(spike,.24,.75)
checks['shared_tile_boundary_identical']=bool(np.array_equal(spike[0]['vertices'][[1,2]],spike[1]['vertices'][[0,3]]))
checks['synthetic_ridge_bounded']=b['final_maximum_triangle_grade']<=.241
checks['nonzero_derived_correction']=b['max_height_correction_m']>.01
try:fair_pavement(chunks(True),.24,.001)
except RuntimeError as error:checks['oversized_correction_rejected']='declared engineering bound' in str(error)
else:checks['oversized_correction_rejected']=False
report={'passed':all(checks.values()),'checks':checks,'plane':a,'synthetic_ridge':b,
        'scope':'Analytic solver invariants only; native road collision and real vehicle trials are required separately'}
(root/'results/pavement_solver_checks.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'passed':report['passed'],'checks':checks},indent=2))
if not report['passed']:raise SystemExit(1)
