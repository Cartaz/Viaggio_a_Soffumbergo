"""Recheck the three visually reviewed bank samples, without metric photo claims."""
import json
import argparse
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--manifest',type=Path)
p.add_argument('--output',type=Path,default=root/'results/steep_bank_preservation.json')
args=p.parse_args()
old=json.loads((root/'terrain/road_design/3f0aee578bac/manifest.json').read_text())
current=json.loads((args.manifest or Path(json.loads((root/'parameters/current_road_design.json').read_text())['manifest'])).read_text())
base=json.loads((root/'terrain/world_tiles/manifest.json').read_text())
observations=json.loads((root/'results/territory/steep_bank_review_20261023.json').read_text())
original={t['id']:t for t in base['tiles']};derived={t['id']:t for t in current['tiles']}
old_earth={e['id']:e for e in old['earthworks']}
rows=[]
for review in observations['observations']:
    name=review['tile'];point=old_earth[name]['peak_change_UE_m'];raw=original[name];tile=derived[name]
    col=round((point[0]*100-tile['location_cm'][0])/50)
    row=round((point[1]*100-tile['location_cm'][1])/50)
    def sample(t):return int(np.fromfile(t['heightmap'],'<u2').reshape(t['samples'],t['samples'])[row,col])
    source=sample(raw);now=sample(tile)
    rows.append({'tile':name,'position_UE_m':point[:2],
                 'source_r16':source,'current_r16':now,'source_preserved_exactly':source==now,
                 'previous_grading_delta_m':old_earth[name]['peak_delta_m'],
                 'current_grading_delta_m':(now-source)*base['height_quantization_m'],
                 'streetview_url':review['url']})
report={'build_id':current['build_id'],'previous_build_id':old['build_id'],
        'scope':'Three reviewed source-bank samples outside asphalt; not a road alignment or full-territory fidelity certificate',
        'all_reviewed_source_samples_preserved':all(r['source_preserved_exactly'] for r in rows),'samples':rows,
        'max_remaining_grading_delta_m':current['report']['max_earthworks_delta_m']}
args.output.write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
if not report['all_reviewed_source_samples_preserved']:raise SystemExit(1)
