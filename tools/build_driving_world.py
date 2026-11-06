"""Full candidate road + separate graded native-terrain derivative.

Original DTM, raw Unreal maps, old projects and observed metadata are immutable.
Bridge engineering dimensions are explicit; diagnostic approach fits are not
surveyed deck elevations. Geometry is versioned by all relevant input hashes.
"""
import hashlib
import argparse
import json
import math
from pathlib import Path
import numpy as np
import shapely
from pyproj import Transformer
from road_geometry import design_profile, SegmentIndex, road_footprint, triangulate_surface
from road_clearance import support_caps
from road_alignment import align_observed_benches
from road_surface_fairing import fair_pavement

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--config',type=Path,default=ROOT/'parameters/road_design.json')
parser.add_argument('--no-activate',action='store_true',help='Write a versioned draft, preserving the active world pointer and report')
args=parser.parse_args()
CONFIG=args.config.resolve()
ROUTE=(Path(__file__).resolve().parents[1] / 'data/geography/circuito_osm_candidate_20261020.geojson')
cfg=json.loads(CONFIG.read_text())
base=json.loads((ROOT/'terrain/world_tiles/manifest.json').read_text())
mosaic=json.loads((ROOT/'terrain/lidar_mosaic/manifest.json').read_text())
heights=np.load(ROOT/'terrain/lidar_mosaic/height_m.npy',mmap_mode='r')
origin=np.asarray(base['origin_ENH_m'])
e0,n0=mosaic['origin_E_N_m'];step=mosaic['step_m']
projection=Transformer.from_crs(4326,6708,always_xy=True)
bridge_source=json.loads((ROOT/'results/territory/bridge_review.json').read_text())['bridges']
network_path=(Path(__file__).resolve().parents[1] / 'data/geography/osm_regional_roads_20261020.geojson')

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
fingerprints={str(p):digest(p) for p in [CONFIG,ROUTE,Path(__file__),ROOT/'tools/road_geometry.py',ROOT/'tools/road_clearance.py',
 ROOT/'Unreal/Source/SoffumbergoTerrainEditor/CircuitMesh.cpp',ROOT/'terrain/lidar_mosaic/manifest.json',
 ROOT/'results/territory/bridge_review.json']}
fingerprints[str(network_path)]=digest(network_path)
if cfg.get('bench_alignment'):
    alignment_path=(ROOT/cfg['bench_alignment']).resolve()
    for path in [alignment_path,ROOT/'tools/road_alignment.py']:
        fingerprints[str(path)]=digest(path)
    alignment_config=json.loads(alignment_path.read_text())
    for name in alignment_config.get('source_reviews',[alignment_config.get('source_review')]):
        if name:
            path=ROOT/name;fingerprints[str(path)]=digest(path)
if cfg.get('pavement_maximum_grade'):
    path=ROOT/'tools/road_surface_fairing.py';fingerprints[str(path)]=digest(path)
build_id=hashlib.sha256(json.dumps(fingerprints,sort_keys=True).encode()).hexdigest()[:12]
folder=ROOT/'terrain/road_design'/build_id;folder.mkdir(parents=True,exist_ok=True)
content='/Game/World/Driving/D_'+build_id

def sample(x,y):
    x,y=np.broadcast_arrays(np.asarray(x),np.asarray(y))
    xx=(x+origin[0]-e0)/step;yy=(n0-origin[1]+y)/step
    c=np.floor(xx).astype(int);r=np.floor(yy).astype(int);dx=xx-c;dy=yy-r
    if np.any((c<0)|(r<0)|(c>=heights.shape[1]-1)|(r>=heights.shape[0]-1)):
        raise ValueError('Outside available mosaic')
    a,b,d,e=heights[r,c],heights[r,c+1],heights[r+1,c],heights[r+1,c+1]
    return (1-dy)*((1-dx)*a+dx*b)+dy*((1-dx)*d+dx*e)-origin[2]

bridges=[]
for item in bridge_source:
    if item['crossing_role']=='adjacent_junction_bridge':continue
    if item['crossing_role']!='traversed_span':raise ValueError('Partial bridge overlap requires review')
    if item['status']!='mapped_span_and_visual_bridge_confirmed_dimensions_unmeasured':raise ValueError('Unreviewed bridge')
    en=np.asarray(item['coordinates_EN_m']);xy=np.column_stack([en[:,0]-origin[0],origin[1]-en[:,1]])
    a,b=xy[[0,-1]];length=np.linalg.norm(b-a);direction=(b-a)/length;normal=np.array([-direction[1],direction[0]])
    lo,hi=cfg['bridge_approach_fit_m']
    s=np.r_[np.arange(-hi,-lo+0.01,1),np.arange(length+lo,length+hi+0.01,1)]
    q=a+s[:,None]*direction;z=sample(q[:,0],q[:,1]);fit=np.polyfit(s,z,1)
    width=cfg['major_road_width_m'] if item['properties'].get('highway')=='secondary' else cfg['width_m']
    bridges.append({**item,'a':a,'direction':direction,'normal':normal,'length':length,'fit':fit,'width_m':width,
                    'footprint':shapely.LineString(xy).buffer(width/2,cap_style='flat')})

def bridge_at(xy,margin=0):
    for b in bridges:
        d=xy-b['a'];along=d@b['direction'];cross=d@b['normal']
        inside=(along>=-margin)&(along<=b['length']+margin)&(np.abs(cross)<=b['width_m']/2+margin)
        yield b,inside,along,cross

route=[];labels=[]
for f in json.loads(ROUTE.read_text())['features']:
    en=np.asarray([projection.transform(*p[:2]) for p in f['geometry']['coordinates']])
    xy=np.column_stack([en[:,0]-origin[0],origin[1]-en[:,1]])
    dense=[]
    for a,b in zip(xy,xy[1:]):
        count=max(1,math.ceil(np.linalg.norm(b-a)/2))
        dense.extend(a+(b-a)*t/count for t in range(count))
    dense=np.vstack([dense,xy[-1]])
    z=sample(dense[:,0],dense[:,1])
    if not np.isfinite(z).all():raise ValueError('Missing route source height')
    route.append({'sector':f['properties']['sector'],'points_m':np.column_stack([dense[:,0],z,dense[:,1]]).tolist()})
    labels.extend([f['properties']['sector']]*(len(dense)-1))
# Fit bridge approaches along the actual routed road, which may bend at the
# abutment. Extending a bridge's straight axis into a hillside samples the cut
# face and can invent a vertical jump at the junction. Only exact span points
# are replaced, before the common continuous longitudinal fit.
flat=np.concatenate([np.asarray(r['points_m'])[:-1] for r in route])
closed=np.vstack([flat,flat[0]])
flat_s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(closed[:,[0,2]],axis=0),axis=1))]
for b in bridges:
    d=flat[:,[0,2]]-b['a'];along=d@b['direction'];cross=d@b['normal']
    on=(along>=-.001)&(along<=b['length']+.001)&(np.abs(cross)<.03)
    ids=np.flatnonzero(on);runs=np.split(ids,np.flatnonzero(np.diff(ids)>1)+1)
    fits=[]
    for run in runs:
        if len(run)<2:continue
        first,last=flat_s[run[0]],flat_s[run[-1]]
        lo,hi=cfg['bridge_approach_fit_m']
        q=np.r_[np.arange(first-hi,first-lo+.01),np.arange(last+lo,last+hi+.01)]
        qx=np.interp(q,flat_s,closed[:,0]);qy=np.interp(q,flat_s,closed[:,2])
        fit=np.polyfit(q-first,sample(qx,qy),1)
        station_from_along=np.polyfit(along[run],flat_s[run]-first,1)
        fits.append([fit[0]*station_from_along[0],fit[1]+fit[0]*station_from_along[1]])
    if not fits:raise ValueError('Bridge not found on routed axis '+b['id'])
    b['fit']=np.mean(fits,axis=0)
    b['approach_fit_method']='linear regression along actual routed approach, outside mapped span; not a surveyed deck'
    flat[on,1]=np.polyval(b['fit'],along[on])
offset=0
for r in route:
    points=np.asarray(r['points_m']);count=len(points)-1
    points[:-1,1]=flat[offset:offset+count,1]
    points[-1,1]=flat[(offset+count)%len(flat),1]
    r['points_m']=points.tolist();offset+=count
profile,raw,station,angles,stats=design_profile(route,cfg['profile_radius_m'],cfg['surface_offset_m'])
source_profile=profile.copy();alignment=None
if cfg.get('bench_alignment'):
    corrected,alignment=align_observed_benches(profile,raw,sample,json.loads(alignment_path.read_text()))
    offset=0
    for section in route:
        points=np.asarray(section['points_m']);count=len(points)-1
        points[:-1]=corrected[offset:offset+count]
        points[-1]=corrected[(offset+count)%len(corrected)]
        section['points_m']=points.tolist();offset+=count
    profile,raw,station,angles,stats=design_profile(route,cfg['profile_radius_m'],cfg['surface_offset_m'])
profile[-1]=profile[0]
index=SegmentIndex(profile)
footprint=road_footprint(profile,cfg['width_m']).simplify(.001,preserve_topology=True)
major=[]
axis=shapely.LineString(profile[:,[0,2]])
for feature in json.loads(network_path.read_text())['features']:
    if feature['properties'].get('highway')!='secondary':continue
    geometry=shapely.transform(shapely.geometry.shape(feature['geometry']),projection.transform,interleaved=False)
    geometry=shapely.transform(geometry,lambda p:np.column_stack([p[:,0]-origin[0],origin[1]-p[:,1]]))
    near=axis.intersection(geometry.buffer(.03))
    if not near.is_empty:major.append(near)
if major:footprint=shapely.union_all([footprint,shapely.union_all(major).buffer(cfg['major_road_width_m']/2,quad_segs=4)]).simplify(.001,preserve_topology=True)
all_bridges=shapely.union_all([b['footprint'] for b in bridges])
bridge_shoulder_exclusion=shapely.union_all([
    shapely.LineString([b['a'],b['a']+b['direction']*b['length']]).buffer(
        b['width_m']/2+cfg['shoulder_m']+.05,cap_style='flat') for b in bridges])
# Earthen shoulders belong to the approaches and banks, not to the air beside
# a bridge slab. Flat caps retain the actual junction beyond each abutment.
shoulder_polygon=footprint.buffer(cfg['shoulder_m'],quad_segs=4).difference(footprint).difference(bridge_shoulder_exclusion)
corridor=footprint.buffer(cfg['shoulder_m']+cfg['blend_m']+1)
shapely.prepare(corridor)

def mesh_record(vertices,triangles,origin_cm,name,kind):
    v=np.asarray(vertices,dtype=float);v=v[:,[0,2,1]]*100-np.asarray(origin_cm)
    t=np.asarray(triangles,dtype=int)
    if not np.isfinite(v).all():raise ValueError('Nonfinite geometry')
    v=np.round(v,5)
    cross=np.cross(v[t[:,1]]-v[t[:,0]],v[t[:,2]]-v[t[:,0]])
    keep=(cross*cross).sum(1)>=1.e-8
    removed=int(np.count_nonzero(~keep));t=t[keep]
    if not len(t):raise ValueError('No nondegenerate faces')
    data={'vertices_cm':v.tolist(),'triangles':t.tolist(),'degenerate_triangles_removed':removed}
    path=folder/(name+'.json');path.write_text(json.dumps(data,separators=(',',':')))
    return {'id':name,'kind':kind,'source':str(path),'sha256':digest(path),'asset':content+'/Meshes/'+name,
            'location_cm':list(origin_cm),'vertices':len(v),'triangles':len(t),'degenerate_triangles_removed':removed}

road_records=[];global_faces=[];tile_polygons={};road_chunks=[]
for tile in base['tiles']:
    bounds=np.asarray(tile['bounds_xy_cm'])/100
    part=footprint.intersection(shapely.box(*bounds))
    if part.is_empty or part.area<1e-7:continue
    v,t=triangulate_surface(part,index,cfg['mesh_max_edge_m'],cfg['major_road_width_m']/2+.05)
    if not t:continue
    road_chunks.append({'vertices':np.asarray(v),'triangles':np.asarray(t),'tile':tile})
    tile_polygons[tile['id']]=part
    print('ROAD_MESH '+tile['id'],flush=True)

pavement_fairing=None
if cfg.get('pavement_maximum_grade'):
    pavement_fairing=fair_pavement(road_chunks,cfg['pavement_maximum_grade'],cfg['pavement_maximum_correction_m'])
for chunk in road_chunks:
    tile=chunk['tile'];positions=chunk['vertices'];triangles=chunk['triangles']
    global_faces.append(positions[triangles])
    at=[tile['location_cm'][0],tile['location_cm'][1],0]
    road_records.append({**mesh_record(positions,triangles,at,'Road_'+tile['id'],'asphalt'),'tile':tile['id']})

# The actual triangle surface, not just the analytic centerline, controls the
# underlying cut/fill. This keeps terrain below the built carriageway.
faces=np.concatenate(global_faces)
face_xy=faces[:,:,[0,2]]
triangle_geometries=shapely.polygons(face_xy)
surface_tree=shapely.STRtree(triangle_geometries)

def surface(x,y):
    x,y=np.broadcast_arrays(x,y);p=np.column_stack([x.ravel(),y.ravel()])
    pairs,dist=surface_tree.query_nearest(shapely.points(p),all_matches=False,return_distance=True)
    chosen=np.empty(len(p),dtype=int);distance=np.empty(len(p))
    chosen[pairs[0]]=pairs[1];distance[pairs[0]]=dist
    tri=face_xy[chosen];a,b,c=tri[:,0],tri[:,1],tri[:,2]
    ab=b-a;ac=c-a;q=p-a
    den=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
    u=(q[:,0]*ac[:,1]-q[:,1]*ac[:,0])/den
    v=(ab[:,0]*q[:,1]-ab[:,1]*q[:,0])/den
    outside=(u<0)|(v<0)|(u+v>1)
    if outside.any():
        ids=np.flatnonzero(outside);pp=p[ids];tt=tri[ids]
        aa=tt;dd=np.roll(tt,-1,axis=1)-aa
        frac=np.clip(((pp[:,None]-aa)*dd).sum(2)/(dd*dd).sum(2),0,1)
        nearest=aa+frac[:,:,None]*dd
        edge=np.argmin(((nearest-pp[:,None])**2).sum(2),axis=1)
        q[ids]=nearest[np.arange(len(ids)),edge]-a[ids]
        u[ids]=(q[ids,0]*ac[ids,1]-q[ids,1]*ac[ids,0])/den[ids]
        v[ids]=(ab[ids,0]*q[ids,1]-ab[ids,1]*q[ids,0])/den[ids]
    z=faces[chosen,:,1]
    out=z[:,0]+u*(z[:,1]-z[:,0])+v*(z[:,2]-z[:,0])
    return out.reshape(x.shape),distance.reshape(x.shape)

graded_arrays={};hole_arrays={};tiles=[];earthworks=[];bridge_clipped=0
support_capped_samples=0;max_support_lowering=0.
quant=base['height_quantization_m'];minimum=base['source_height_bounds_m'][0]
for tile in base['tiles']:
    item=dict(tile);n=tile['samples'];x0,y0=tile['location_cm'][:2]
    x=x0/100+np.arange(n)*step;y=y0/100+np.arange(n)*step
    xx,yy=np.meshgrid(x,y)
    mask=shapely.contains_xy(corridor,xx,yy)
    if not mask.any():tiles.append(item);continue
    encoded=np.fromfile(tile['heightmap'],dtype='<u2').reshape(n,n).copy()
    holes=np.fromfile(tile['holes'],dtype='u1').reshape(n,n).copy()
    old=encoded.astype(float)*quant+minimum-origin[2];new=old.copy()
    # No synthetic filling at absent source samples, including shoulders.
    mask&=holes==0
    px,py=xx[mask],yy[mask]
    level,distance=surface(px,py)
    # A wide smooth blend erases cliffs and fills roadside stream banks.
    # Preserve those source features by narrowing the engineered transition
    # when the measured bank differs substantially from the carriageway.
    steep=np.clip((np.abs(old[mask]-level)-cfg['steep_transition_start_m'])/cfg['steep_transition_start_m'],0,1)
    shoulder=cfg['shoulder_m']+(cfg['steep_shoulder_m']-cfg['shoulder_m'])*steep
    blend=cfg['blend_m']+(cfg['steep_blend_m']-cfg['blend_m'])*steep
    t=np.clip((distance-shoulder)/blend,0,1)
    weight=1-t*t*(3-2*t)
    desired=old[mask]+(level-cfg['terrain_clearance_m']-old[mask])*weight
    clip=np.zeros(len(px),dtype=bool);in_bridge=np.zeros(len(px),dtype=bool)
    p=np.column_stack([px,py])
    for b,inside,s,cross in bridge_at(p):
        # Keep the original low bed. If source instead includes/interpolates
        # the bridge surface, mask that surface rather than inventing a bed.
        in_bridge|=(s>=0)&(s<=b['length'])&(np.abs(cross)<=b['width_m']/2+cfg['shoulder_m']+cfg['blend_m']+1)
        deck=level
        # Visibility/collision is interpolated over a native Landscape cell.
        # Pad the unreliable source-deck footprint so an unmasked corner just
        # outside the span cannot close the hole or protrude through its edge.
        # Heights remain source values below the span; no river bed is filled.
        padding=step*math.sqrt(2)*cfg['bridge_visibility_padding_cells']
        clip_footprint=(s>1-padding)&(s<b['length']-1+padding)&(np.abs(cross)<=b['width_m']/2+padding)
        clip|=clip_footprint&(old[mask]>deck-cfg['bridge_unknown_ground_clip_clearance_m'])
    desired[in_bridge]=old[mask][in_bridge]
    for b,inside,s,cross in bridge_at(p):
        # Preserve low measured beds; the abutment samples that remain visible
        # must sit below the actual built asphalt, including its smooth grade.
        abutment=inside&~clip&(old[mask]>level-cfg['terrain_clearance_m'])
        desired[abutment]=level[abutment]-cfg['terrain_clearance_m']
    # Bound the whole native cell, including roads crossing between its nodes.
    # Keep bridge interiors governed by the measured-bed/visibility policy.
    bridge_interior=np.zeros(len(px),dtype=bool)
    for b,inside,s,cross in bridge_at(p):
        bridge_interior|=inside&(s>1)&(s<b['length']-1)
    # Also cap clipped abutment vertices: even a hidden vertex contributes
    # height to an adjacent visible cell. Interior measured beds stay intact.
    candidates=(distance<=step*math.sqrt(2)+1.e-8)&~bridge_interior
    caps=support_caps(px[candidates],py[candidates],faces,surface_tree,triangle_geometries,step,cfg['terrain_clearance_m'])
    before=desired[candidates].copy()
    desired[candidates]=np.minimum(before,caps)
    support_capped_samples+=int(np.count_nonzero(desired[candidates]<before))
    if len(before):max_support_lowering=max(max_support_lowering,float(np.max(before-desired[candidates])))
    new[mask]=desired
    holes_at=holes[mask];holes_at[clip]=255;holes[mask]=holes_at;bridge_clipped+=int(clip.sum())
    delta=new-old
    encoded[mask]=np.rint((new[mask]+origin[2]-minimum)/quant).astype('<u2')
    if np.any((new[mask]+origin[2]<minimum)|(new[mask]+origin[2]>base['source_height_bounds_m'][1])):raise ValueError('Quantizer overflow')
    hp=folder/(tile['id']+'.r16');vp=folder/(tile['id']+'.holes')
    hp.write_bytes(encoded.tobytes());vp.write_bytes(holes.tobytes())
    peak=np.unravel_index(np.argmax(np.abs(delta)),delta.shape)
    item.update({'raw_map':tile['map'],'map':content+'/Terrain/'+tile['id'],'heightmap':str(hp),'holes':str(vp),
                 'height_sha256':digest(hp),'holes_sha256':digest(vp),'engineering_terrain':True,
                 'max_grading_delta_m':float(np.abs(delta[mask]).max()),'changed_samples':int(np.count_nonzero(delta[mask])),
                 'peak_change_UE_m':[float(xx[peak]),float(yy[peak]),float(new[peak])],
                 'peak_source_height_local_m':float(old[peak]),'peak_delta_m':float(delta[peak])})
    tiles.append(item);graded_arrays[tile['id']]=encoded;hole_arrays[tile['id']]=holes
    earthworks.append({k:item[k] for k in ['id','max_grading_delta_m','changed_samples','peak_change_UE_m','peak_source_height_local_m','peak_delta_m']})
    print('GRADED_TERRAIN '+tile['id']+' '+str(item['max_grading_delta_m']),flush=True)

lookup={(t['tx'],t['ty']):t for t in tiles}
def raster(tile):
    return graded_arrays.get(tile['id']) if tile['id'] in graded_arrays else np.fromfile(tile['heightmap'],'<u2').reshape(1009,1009)
def holes_for(tile):
    return hole_arrays.get(tile['id']) if tile['id'] in hole_arrays else np.fromfile(tile['holes'],'u1').reshape(1009,1009)
seams=[]
for key,tile in lookup.items():
    a=raster(tile);av=holes_for(tile)
    for dx,dy in [(1,0),(0,1)]:
        other=lookup.get((key[0]+dx,key[1]+dy))
        if not other:continue
        b=raster(other);bv=holes_for(other)
        aa,bb=(a[:,-1],b[:,0]) if dx else (a[-1,:],b[0,:])
        ah,bh=(av[:,-1],bv[:,0]) if dx else (av[-1,:],bv[0,:])
        count=int(np.count_nonzero(aa!=bb)+np.count_nonzero(ah!=bh))
        seams.append({'a':tile['id'],'b':other['id'],'mismatches':count})
        if count:raise ValueError('Derived global seam differs '+tile['id']+' '+other['id'])

def ground(x,y):
    # Source global grid coordinates, same diagonal as native Landscape.
    x,y=np.broadcast_arrays(x,y);out=np.empty(x.shape)
    c=(x+origin[0]-e0)/step;r=(n0-origin[1]+y)/step
    col=np.floor(c).astype(int);row=np.floor(r).astype(int);fx=c-col;fy=r-row
    tx=col//1008;ty=row//1008
    for k in np.unique(np.column_stack([tx.ravel(),ty.ravel()]),axis=0):
        mask=(tx==k[0])&(ty==k[1]);tile=lookup[tuple(k)];a=raster(tile)
        lx=col[mask]-k[0]*1008;ly=row[mask]-k[1]*1008
        z00=a[ly,lx].astype(float);z10=a[ly,lx+1].astype(float);z01=a[ly+1,lx].astype(float);z11=a[ly+1,lx+1].astype(float)
        xx,yy=fx[mask],fy[mask]
        z=np.where(xx>=yy,z00+(z10-z00)*xx+(z11-z10)*yy,z00+(z11-z01)*xx+(z01-z00)*yy)
        out[mask]=z*quant+minimum-origin[2]
    return out

shoulder_records=[]
for tile in tiles:
    if tile['id'] not in tile_polygons:continue
    bounds=np.asarray(tile['bounds_xy_cm'])/100
    part=shoulder_polygon.intersection(shapely.box(*bounds))
    if part.is_empty or part.area<1e-7:continue
    # Triangulation only asks the profile for initial placeholder heights;
    # actual elevations blend from the road edge to the derived native raster.
    boundary_diagnostics={}
    v,t=triangulate_surface(part,index,cfg['mesh_max_edge_m'],cfg['major_road_width_m']/2+cfg['shoulder_m']+.1,
                            allow_boundary_collapse=True,diagnostics=boundary_diagnostics)
    if not t:continue
    v=np.asarray(v);z,d=surface(v[:,0],v[:,2]);g=ground(v[:,0],v[:,2])+.02
    w=np.clip(d/cfg['shoulder_m'],0,1);v[:,1]=z*(1-w)+g*w
    shoulder_records.append({**mesh_record(v,t,[tile['location_cm'][0],tile['location_cm'][1],0],'Shoulder_'+tile['id'],'shoulder'),
                             'tile':tile['id'],'boundary_quantization':boundary_diagnostics})

bridge_records=[]
def box_mesh(center,direction,length,width,height):
    d=np.r_[direction,0];side=np.array([-direction[1],direction[0],0]);up=np.array([0,0,1])
    center=np.asarray(center);corners=[]
    for z in [-.5,.5]:
        for x,y in [(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)]:corners.append(center+d*x*length+side*y*width+up*z*height)
    faces=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]]
    return np.asarray(corners)[:,[0,2,1]],np.asarray(faces)
for b in bridges:
    verts=[];tri=[]
    def add_box(c,l,w,h):
        v,t=box_mesh(c,b['direction'],l,w,h);tri.extend((t+len(verts)).tolist());verts.extend(v.tolist())
    mid=b['a']+b['direction']*b['length']/2;top=float(surface(mid[0],mid[1])[0])
    # Clip the actual asphalt triangles for the slab roof. A single four-corner
    # box can protrude through a curved approach even when all corners are low.
    for face_id in surface_tree.query(b['footprint'],predicate='intersects'):
        part=triangle_geometries[face_id].intersection(b['footprint'])
        if part.is_empty or part.area<1.e-10 or part.geom_type!='Polygon':continue
        xy=np.asarray(part.exterior.coords)[:-1]
        face=faces[face_id];aa=face[0,[0,2]];ab=face[1,[0,2]]-aa;ac=face[2,[0,2]]-aa;q=xy-aa
        den=ab[0]*ac[1]-ab[1]*ac[0]
        u=(q[:,0]*ac[1]-q[:,1]*ac[0])/den;v=(ab[0]*q[:,1]-ab[1]*q[:,0])/den
        h=face[0,1]+u*(face[1,1]-face[0,1])+v*(face[2,1]-face[0,1])-.025
        start=len(verts);count=len(xy)
        verts.extend(np.column_stack([xy[:,0],h,xy[:,1]]).tolist())
        verts.extend(np.column_stack([xy[:,0],h-cfg['bridge_deck_thickness_m'],xy[:,1]]).tolist())
        for k in range(1,count-1):
            face_indices=[start,start+k,start+k+1]
            cross=(xy[k,0]-xy[0,0])*(xy[k+1,1]-xy[0,1])-(xy[k,1]-xy[0,1])*(xy[k+1,0]-xy[0,0])
            if cross<0:face_indices=face_indices[::-1]
            tri.append(face_indices);tri.append([i+count for i in face_indices[::-1]])
    edge=np.asarray(shapely.segmentize(b['footprint'],2).exterior.coords)
    edge_height=surface(edge[:,0],edge[:,1])[0]-.025
    for k in range(len(edge)-1):
        start=len(verts)
        for j,dz in [(k,0),(k+1,0),(k+1,-cfg['bridge_deck_thickness_m']),(k,-cfg['bridge_deck_thickness_m'])]:
            verts.append([float(edge[j,0]),float(edge_height[j]+dz),float(edge[j,1])])
        tri.extend([[start,start+1,start+2],[start,start+2,start+3]])
    slab=mesh_record(verts,tri,[*list(mid*100),0],'Deck_'+b['id'].split('/')[-1],'concrete')
    # Original generic steel barriers, placed only where Street View confirms them.
    verts=[];tri=[]
    for side in [-1,1]:
        lateral=b['normal']*side*(b['width_m']/2+.07)
        for s in np.arange(.8,b['length']-.5,cfg['bridge_rail_post_spacing_m']):
            xy=b['a']+b['direction']*s+lateral;z=float(surface(xy[0],xy[1])[0])
            add_box([*xy,z+cfg['bridge_rail_height_m']/2],.13,.13,cfg['bridge_rail_height_m'])
        for s in np.arange(.8,b['length']-.8,2):
            ln=min(2,b['length']-.8-s);xy=b['a']+b['direction']*(s+ln/2)+lateral;z=float(np.polyval(b['fit'],s+ln/2)+cfg['surface_offset_m'])
            for dz in [.55,.95]:add_box([*xy,z+dz],ln,.13,.15)
    rails=mesh_record(verts,tri,[*list(mid*100),0],'Rails_'+b['id'].split('/')[-1],'metal')
    owner=min(tiles,key=lambda t:shapely.box(*(np.asarray(t['bounds_xy_cm'])/100)).distance(shapely.Point(mid)))
    slab['tile']=rails['tile']=owner['id'];bridge_records.extend([slab,rails])

survey=[]
for p in profile[:-1]:
    z,_=surface(p[0],p[2]);survey.append([p[0]*100,p[2]*100,float(z)*100])
delta=np.diff(profile,axis=0);grade=np.abs(delta[:,1]/np.diff(station))
reversals=np.where(angles>179.99)[0]
report={'build_id':build_id,'fingerprints':fingerprints,'config':cfg,'source_tiles':len(tiles),
        'graded_tiles':len(earthworks),'road_tiles':len(road_records),'road_triangles':sum(r['triangles'] for r in road_records),
        'route_length_horizontal_m':float(station[-1]),'max_design_grade_percent':float(grade.max()*100),
        'grade_over_20_percent_segments':int(np.count_nonzero(grade>.2)),
        'max_earthworks_delta_m':max(e['max_grading_delta_m'] for e in earthworks),
        'bridge_source_surface_samples_masked':bridge_clipped,
        'support_cell_capped_samples':support_capped_samples,'max_support_cell_additional_lowering_m':max_support_lowering,
        'preserved_reversals':[{'sector':labels[i],'station_m':float(station[i]),'point_UE_m':profile[i,[0,2,1]].tolist()} for i in reversals],
        'source_route_xy_unchanged':alignment is None,'source_geometry_file_modified':False,
        'source_rasters_modified':False,'source_unreal_maps_modified':False,
        'seams_equal':True,'shared_edges_checked':len(seams),'native_imported':False,'full_lap_driven':False,**stats}
manifest={'build_id':build_id,'content_root':content,'origin_ENH_m':origin.tolist(),'config':cfg,'report':report,'tiles':tiles,
          'meshes':road_records+shoulder_records+bridge_records,'road_survey_points_cm':survey,
          'profile_UE_cm':(profile[:,[0,2,1]]*100).tolist(),'profile_station_m':station.tolist(),
          'sectors':labels,'seams':seams,'earthworks':earthworks,
          'spawn':{'position_cm':[survey[0][0],survey[0][1],survey[0][2]+45],
                   'yaw_deg':math.degrees(math.atan2(profile[1,2]-profile[0,2],profile[1,0]-profile[0,0]))}}
if alignment is not None:
    manifest['alignment_review']=alignment
    manifest['source_reference_profile_UE_cm']=(source_profile[:,[0,2,1]]*100).tolist()
if pavement_fairing is not None:
    manifest['pavement_fairing']=pavement_fairing
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
if not args.no_activate:
    (ROOT/'parameters/current_road_design.json').write_text(json.dumps({'manifest':str(folder/'manifest.json'),'build_id':build_id},indent=2))
    (ROOT/'results/road_design_report.json').write_text(json.dumps(report,indent=2))
else:
    (ROOT/('results/road_design_draft_'+build_id+'.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
