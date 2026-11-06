"""Find open internal breaks from actual exported rail/wall end rectangles."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise RuntimeError('Preserve earlier connectivity evidence')
    m=json.loads(args.manifest.read_text());s=m['roadside_structures'];rows=[]
    for mesh in s['records']:
        data=json.loads(Path(mesh['source']).read_text())
        solids=(np.asarray(data['vertices_cm'])+mesh['location_cm']).reshape(-1,8,3)/100
        sections={};segments=[]
        for solid in solids:
            length=np.linalg.norm(solid[1,:2]-solid[0,:2])
            if mesh['kind']=='metal' and abs(length-s['config']['guardrail_post_width_m'])<1.e-5:continue
            ends=[]
            for indices in [[0,3,4,7],[1,2,5,6]]:
                # Rounding only absorbs the documented 0.00001 cm source precision.
                token=tuple(sorted(map(tuple,np.round(solid[indices],7))))
                ends.append(sections.setdefault(token,len(sections)))
            segments.append(ends)
        adjacent={i:set() for i in range(len(sections))}
        for a,b in segments:adjacent[a].add(b);adjacent[b].add(a)
        remaining=set(adjacent);components=0
        while remaining:
            components+=1;stack=[remaining.pop()]
            while stack:
                for node in adjacent[stack.pop()]:
                    if node in remaining:remaining.remove(node);stack.append(node)
        degrees=[len(v) for v in adjacent.values()]
        ends=degrees.count(1);branches=sum(v>2 for v in degrees)
        rows.append({'mesh_id':mesh['id'],'segments':len(segments),'connected_chains':components,
            'open_ends':ends,'branch_sections':branches,
            'source_signature_matches':hashlib.sha256(Path(mesh['source']).read_bytes()).hexdigest()==mesh['sha256'],
            'passed':components==1 and ends==2 and branches==0})
    report={'build_id':m['build_id'],'passed':all(r['passed'] and r['source_signature_matches'] for r in rows),
        'meshes':rows,'scope':'Each of the eight existing local rail/wall records must form one connected open chain. This does not establish observed real-world extents, wall exposure or native collision.'}
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
