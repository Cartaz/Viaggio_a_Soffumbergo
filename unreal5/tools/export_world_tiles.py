"""Export the entire valid LiDAR mosaic as native Landscape-sized tiles and holes."""
import hashlib,json,math
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[1]
source=root/'terrain/lidar_mosaic'
m=json.loads((source/'manifest.json').read_text())
data=np.load(source/'height_m.npy',mmap_mode='r')
out=root/'terrain/world_tiles';out.mkdir(parents=True,exist_ok=True)
origin=json.loads((root/'terrain/valle_first/manifest.json').read_text())['origin_ENH_m']
quads=1008;n=quads+1;step=m['step_m'];e0,n0=m['origin_E_N_m']
# Global encoding guarantees identical height integers and transforms at every shared edge.
minimum=math.floor(min(t['height_min_max_m'][0] for t in m['tiles']))-1
maximum=math.ceil(max(t['height_min_max_m'][1] for t in m['tiles']))+1
quant=(maximum-minimum)/65535
zscale=quant*100*128;zoffset=(minimum-origin[2])*100+32768/128*zscale
tiles=[];valid_total=0
for ty,row in enumerate(range(0,data.shape[0]-1,quads)):
    for tx,col in enumerate(range(0,data.shape[1]-1,quads)):
        endr=min(row+n,data.shape[0]);endc=min(col+n,data.shape[1])
        values=np.asarray(data[row:endr,col:endc])
        if not np.isfinite(values).any():continue
        heights=np.zeros((n,n),dtype='<u2');holes=np.full((n,n),255,dtype='u1')
        valid=np.isfinite(values)
        heights[:values.shape[0],:values.shape[1]]=np.where(valid,np.rint((np.nan_to_num(values,nan=minimum)-minimum)/quant),0).astype('<u2')
        holes[:values.shape[0],:values.shape[1]][valid]=0
        # Missing heights exist only under visibility/collision holes; they never become filled ground.
        name=f'T_{tx:02}_{ty:02}'
        hp=out/(name+'.r16');vp=out/(name+'.holes')
        hp.write_bytes(heights.tobytes());vp.write_bytes(holes.tobytes())
        x=(e0+col*step-origin[0])*100;y=(origin[1]-n0+row*step)*100
        tiles.append({'id':name,'tx':tx,'ty':ty,'map':'/Game/World/Terrain/'+name,
                      'samples':n,'xy_scale_cm':step*100,'z_scale':zscale,'location_cm':[x,y,zoffset],
                      'bounds_xy_cm':[x,y,x+quads*step*100,y+quads*step*100],
                      'heightmap':str(hp),'holes':str(vp),'valid_samples':int(valid.sum()),
                      'source_window':[row,col,endr-row,endc-col],
                      'height_sha256':hashlib.sha256(hp.read_bytes()).hexdigest(),'holes_sha256':hashlib.sha256(vp.read_bytes()).hexdigest()})
        valid_total+=int(valid.sum())
seams=[]
lookup={(t['tx'],t['ty']):t for t in tiles}
for key,tile in lookup.items():
    a=np.fromfile(tile['heightmap'],dtype='<u2').reshape(n,n)
    ah=np.fromfile(tile['holes'],dtype='u1').reshape(n,n)
    for delta in [(1,0),(0,1)]:
        other=lookup.get((key[0]+delta[0],key[1]+delta[1]))
        if not other:continue
        b=np.fromfile(other['heightmap'],dtype='<u2').reshape(n,n)
        bh=np.fromfile(other['holes'],dtype='u1').reshape(n,n)
        ae,be=(a[:,-1],b[:,0]) if delta[0] else (a[-1,:],b[0,:])
        av,bv=(ah[:,-1],bh[:,0]) if delta[0] else (ah[-1,:],bh[0,:])
        mismatches=int(np.count_nonzero(ae!=be))+int(np.count_nonzero(av!=bv))
        seams.append({'a':tile['id'],'b':other['id'],'mismatches':mismatches})
        if mismatches:raise RuntimeError('Tile seam mismatch')
manifest={'source':'../lidar_mosaic/manifest.json','origin_ENH_m':origin,'step_m':step,
          'tile_quads':quads,'samples_per_tile':n,'sections_per_component':2,'quads_per_section':63,
          'height_quantization_m':quant,'height_error_max_bound_m':quant/2,
          'source_height_bounds_m':[minimum,maximum],'nodata_policy':'visibility and collision holes; no extrapolation',
          'source_overlap_policy':m['overlap_policy'],'source_overlap_max_difference_m':m['max_overlap_error_m'],
          'tiles':tiles,'seams':seams,'seam_samples_equal':True,'native_import_verified':False}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'tiles':len(tiles),'shared_edges_checked':len(seams),'encoded_seams_exact':True,'quantization_m':quant}))
