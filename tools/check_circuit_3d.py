"""Independent corridor checks, including optional scalar sampling of real sources."""
import argparse
from functools import lru_cache
import json
import math
from pathlib import Path

from build_circuit_3d import ROOT, load_sources
from coffa.dtm_mosaic import choose_source, interior_margin
from coffa.terrain import sample_grid
from register_dtm import sha256_file


def check(manifest_path,input_dir=None):
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert manifest['axes'] == '+X east, +Y up, +Z south'
    assert not manifest['datum_conversion_applied'] and not manifest['road_surface_verified']
    for relative,digest in manifest['source_fingerprints'].items():
        assert sha256_file(ROOT/relative) == digest, 'Generation source/config changed: '+relative
    entries = {tuple(e['offset_xz_m']): e for e in manifest['sectors']}
    assert len(entries) == len(manifest['sectors'])
    source_names = [t['filename'] for t in manifest['source_tiles']]
    arrays = None
    probes = 0
    max_scalar_error = 0.
    if input_dir:
        catalog = {'tiles':manifest['source_tiles']}
        arrays = dict(zip(source_names,load_sources(input_dir,catalog)))
    edges = {}
    for position,entry in entries.items():
        relative = Path(entry['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        path = manifest_path.parent/relative
        assert sha256_file(path) == entry['sha256'], 'Chunk checksum mismatch: '+entry['id']
        s = json.loads(path.read_text(encoding='utf-8'))
        assert s['side'] == 65 and s['step_m'] == 2
        assert len(s['heights_m']) == len(s['normals']) == len(s['source_ids']) == 65*65
        for height,source in zip(s['heights_m'],s['source_ids']):
            assert (height is None) == (source == -1)
            if height is not None:
                assert math.isfinite(height) and 0 <= source < len(source_names)
        assert s['skirt_depth_m'] > max(s['lod_max_error_m'])
        edge_ids = {'n':list(range(65)), 's':list(range(64*65,65*65)),
                    'w':[i*65 for i in range(65)],'e':[i*65+64 for i in range(65)]}
        edges[position] = {name:[[s[field][i] for i in ids] for field in
                                ['heights_m','normals','source_ids']] for name,ids in edge_ids.items()}
        if arrays:
            for row in [0,32,64]:
                for col in [0,32,64]:
                    x,z = position[0]+col*2,position[1]+row*2
                    east,north = manifest['origin_ENH_m'][0]+x,manifest['origin_ENH_m'][1]-z
                    candidates = []
                    a,b,c,d = manifest['config']['valle_region_local_xz_m']
                    pinned = a <= x <= c and b <= z <= d
                    for tile in manifest['source_tiles']:
                        west,south,right,top = tile['bounds_EN_m']
                        if west+.25 <= east <= right-.25 and south+.25 <= north <= top-.25:
                            try:
                                height = sample_grid(arrays[tile['filename']],east,north,west,top)
                            except ValueError:
                                continue
                            candidates.append((tile['filename'],height,
                                               interior_margin(east,north,tile['bounds_EN_m']),
                                               pinned and tile['filename'] in manifest['config']['valle_primary_tiles']))
                    chosen = choose_source(candidates)
                    k = row*65+col
                    if chosen:
                        assert s['source_ids'][k] == source_names.index(chosen[0])
                        error = abs(s['heights_m'][k]-(chosen[1]-manifest['origin_ENH_m'][2]))
                        max_scalar_error = max(error,max_scalar_error)
                        assert error < .000051, 'Scalar source/mesh mismatch'
                    else:
                        assert s['heights_m'][k] is None
                    probes += 1
    seams = 0
    for (x,z),edge in edges.items():
        for dx,dz,a,b in [(128,0,'e','w'),(0,128,'s','n')]:
            neighbor = edges.get((x+dx,z+dz))
            if neighbor:
                assert edge[a] == neighbor[b], 'Shared geometry/provenance mismatch'
                seams += 1
    @lru_cache(maxsize=16)
    def get_sector(x,z):
        return json.loads((manifest_path.parent/entries[(x,z)]['path']).read_text(encoding='utf-8'))
    samples = 0
    for feature in manifest['route']:
        assert len(feature['points_m']) == len(feature['source_ids']) == len(feature['source_spread_m'])
        for x,y,z in feature['points_m']:
            s = get_sector(math.floor(x/128)*128,math.floor(z/128)*128)
            u,v = (x-s['offset_xz_m'][0])/2,(z-s['offset_xz_m'][1])/2
            col,row = min(int(u),63),min(int(v),63)
            u,v = u-col,v-row
            a,b,d,e = [s['heights_m'][k] for k in [row*65+col,row*65+col+1,(row+1)*65+col,(row+1)*65+col+1]]
            assert all(h is not None for h in (a,b,d,e))
            h = a+(b-a)*u+(d-a)*v if u+v <= 1 else e+(d-e)*(1-u)+(b-e)*(1-v)
            assert abs(h-y) < 1e-7
            samples += 1
    for i,feature in enumerate(manifest['route']):
        following = manifest['route'][(i+1)%len(manifest['route'])]
        assert math.dist(feature['points_m'][-1],following['points_m'][0]) < .003
    result = {'manifest_sha256':sha256_file(manifest_path),'sector_count':len(entries),
              'shared_edges_checked':seams,'route_mesh_samples_checked':samples,
              'scalar_real_source_probes':probes,'max_scalar_source_error_m':max_scalar_error,
              'source_priority_checked_independently':bool(arrays)}
    print(json.dumps(result,indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--input-dir',type=Path)
    args = parser.parse_args()
    check(args.manifest,args.input_dir)
