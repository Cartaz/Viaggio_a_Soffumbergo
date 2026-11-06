"""Append source-backed draped wire net and foot curb without changing LiDAR/road.

Wire dimensions, coverage height and photo-to-profile placements are engineering
choices. The source establishes an anthropic net, not a surveyed design.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import shapely
from pyproj import Transformer
from road_surface import RoadSurface
from prepare_reentry_checks import NativeGround
from prepare_roadside_structures import boundary_point
from roadside_joints import joined_prism, convex_faces

ROOT = Path(__file__).resolve().parents[1]
FACES = np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],
                  [1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--parent-draft', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    parent = args.parent_draft.resolve()
    imported = json.loads((parent/'import_report.json').read_text())
    assert imported['all_imported']
    old_path = Path(imported['manifest'])
    old = json.loads(old_path.read_text())
    config = json.loads(args.config.read_text(encoding='utf-8'))
    inputs = [old_path, parent/'circuit_driving_world.json', parent/'circuit_itinerary.json',
              args.config, Path(__file__), ROOT/'tools/road_surface.py',
              ROOT/'tools/prepare_reentry_checks.py', ROOT/'tools/roadside_joints.py',
              ROOT/'tools/prepare_roadside_structures.py', ROOT/'tools/import_rockfall_edges.py',
              ROOT/'tools/audit_rockfall_edges.py',
              ROOT/'Unreal/Source/SoffumbergoTerrainEditor/CircuitMesh.cpp']
    inputs += [ROOT/p for p in config['source_reviews']]
    fingerprints = {str(p.resolve()): sha(p) for p in inputs}
    build = hashlib.sha256(json.dumps(fingerprints, sort_keys=True).encode()).hexdigest()[:12]
    folder = ROOT/'terrain/rockfall_edges'/build
    draft = ROOT/'results/road_drafts'/build
    if folder.exists() or draft.exists(): raise RuntimeError('Preserve previous candidate')
    folder.mkdir(parents=True); draft.mkdir(parents=True)
    road = RoadSurface(old)
    ground = NativeGround(old)
    raw = NativeGround(json.loads((ROOT/'terrain/world_tiles/manifest.json').read_text()))
    profile = np.asarray(old['profile_UE_cm'])/100
    station = np.asarray(old['profile_station_m'])
    origin = np.asarray(old['origin_ENH_m'])
    project = Transformer.from_crs(4326, 6708, always_xy=True)

    def photo_station(latlon):
        e,n = project.transform(latlon[1], latlon[0])
        p = np.array([e-origin[0], origin[1]-n])
        a = profile[:-1,:2]; d = np.diff(profile[:,:2], axis=0)
        t = np.clip(((p-a)*d).sum(1)/(d*d).sum(1), 0, 1)
        q = a+t[:,None]*d
        i = int(np.argmin(((q-p)**2).sum(1)))
        distance = float(np.linalg.norm(q[i]-p))
        if distance > config['maximum_photo_profile_offset_m']:
            raise ValueError('Photo is too far from the existing engineering profile')
        return {'wgs84':latlon,'station_m':float(station[i]+t[i]*(station[i+1]-station[i])),
                'profile_offset_m':distance,'profile_UE_xy_m':q[i].tolist()}

    net_refs = [photo_station(p) for p in config['net_extent_wgs84']]
    curb_refs = [photo_station(p) for p in config['curb_extent_wgs84']]
    lo,hi = sorted(p['station_m'] for p in net_refs)
    clo,chi = sorted(p['station_m'] for p in curb_refs)
    assert hi-lo > 5 and lo <= clo <= chi <= hi
    samples = np.linspace(lo, hi, int(np.ceil((hi-lo)/config['section_step_m']))+1)
    centers = np.column_stack([np.interp(samples, station, profile[:,j]) for j in range(2)])
    before = np.column_stack([np.interp(samples-.25, station, profile[:,j]) for j in range(2)])
    after = np.column_stack([np.interp(samples+.25, station, profile[:,j]) for j in range(2)])
    tangent = after-before; tangent /= np.linalg.norm(tangent,axis=1)[:,None]
    normal = np.column_stack([-tangent[:,1],tangent[:,0]])
    high = raw.sample(centers+normal*5) > raw.sample(centers-normal*5)
    normal[~high] *= -1
    if np.min((normal[:-1]*normal[1:]).sum(1)) < .8:
        raise ValueError('Uphill side changes abruptly; split the observed run')
    bounds = [*(centers.min(0)*100-1500), *(centers.max(0)*100+1500)]
    ids = road.tree.query(shapely.box(*bounds), predicate='intersects')
    footprint = shapely.transform(shapely.union_all(road.polygons[ids]),lambda p:p/100)
    edges = np.array([boundary_point(c,n,footprint) for c,n in zip(centers,normal)])
    asphalt_z,distance = road.sample(edges*100)
    if distance.max() > .01: raise ValueError('Foot is not on the actual asphalt boundary')
    asphalt_z /= 100
    # Parameter v follows distance ALONG the native bank, avoiding vertically
    # stretched cells on steep slopes. Only the wire is raised above the ground.
    offsets = np.arange(config['net_start_offset_m'],config['bank_scan_width_m']+.00001,.1)
    cross_xy = edges[:,None,:]+normal[:,None,:]*offsets[None,:,None]
    cross_z = ground.sample(cross_xy.reshape(-1,2)).reshape(len(samples),-1)
    if not np.isfinite(cross_z).all(): raise ValueError('Net crosses missing ground')
    arc = np.concatenate([np.zeros((len(samples),1)),np.cumsum(np.sqrt(
        np.diff(cross_z,axis=1)**2+np.diff(offsets)[None,:]**2),axis=1)],axis=1)
    height = config['net_surface_height_m']
    if arc[:,-1].min() < height: raise ValueError('Bank transect is too short')

    def bank_map(uv):
        uv = np.atleast_2d(uv); k = np.clip(np.searchsorted(samples,uv[:,0])-1,0,len(samples)-2)
        t = (uv[:,0]-samples[k])/(samples[k+1]-samples[k])
        r0 = np.array([np.interp(v,arc[i],offsets) for i,v in zip(k,uv[:,1])])
        r1 = np.array([np.interp(v,arc[i+1],offsets) for i,v in zip(k,uv[:,1])])
        xy0 = edges[k]+normal[k]*r0[:,None]
        xy1 = edges[k+1]+normal[k+1]*r1[:,None]
        xy = xy0*(1-t[:,None])+xy1*t[:,None]
        z = ground.sample(xy)+config['net_vertical_standoff_m']
        return np.column_stack([xy,z])

    # Deduplicated hexagonal wire lattice, clipped to the confirmed coverage
    # interval. No texture or image from Street View enters the game assets.
    radius = config['hex_circumradius_m']; h = math.sqrt(3)*radius
    rectangle = shapely.box(lo,0,hi,height); segments = {}
    for i in range(int(math.floor(lo/(1.5*radius)))-1,int(math.ceil(hi/(1.5*radius)))+2):
        for j in range(-1,int(math.ceil(height/h))+2):
            center = np.array([i*1.5*radius,(j+.5*(i%2))*h])
            poly = center+radius*np.column_stack([np.cos(np.arange(6)*math.pi/3),np.sin(np.arange(6)*math.pi/3)])
            for a,b in zip(poly,np.roll(poly,-1,axis=0)):
                line = shapely.LineString([a,b]).intersection(rectangle)
                if line.is_empty or line.geom_type!='LineString' or line.length<1.e-5: continue
                aa,bb = np.asarray(line.coords)[[0,-1]]
                token = tuple(sorted([tuple(np.round(aa,7)),tuple(np.round(bb,7))]))
                segments[token] = [aa,bb]
    param = np.asarray(list(segments.values()))
    # A short wire is subdivided at bank kinks to remain above native triangles.
    parts = []
    for a,b in param:
        count = int(np.ceil(np.linalg.norm(b-a)/config['maximum_wire_piece_m']))
        q = np.linspace(a,b,count+1)
        parts.extend(zip(q[:-1],q[1:]))
    uv = np.asarray(parts)
    for refinement in range(7):
        ends = bank_map(uv.reshape(-1,2)).reshape(-1,2,3)
        q = ends[:,0,None,:]*(1-np.array([.25,.5,.75])[None,:,None])+ends[:,1,None,:]*np.array([.25,.5,.75])[None,:,None]
        gaps = q[:,:,2]-ground.sample(q[:,:,:2].reshape(-1,2)).reshape(-1,3)
        bad = gaps.min(1)<config['minimum_wire_ground_clearance_m']
        if not bad.any():break
        if refinement==6:raise ValueError('Wire still intersects native bank after refinement')
        mid = uv[bad].mean(1)
        uv = np.concatenate([uv[~bad],np.stack([uv[bad,0],mid],axis=1),np.stack([mid,uv[bad,1]],axis=1)])
    d = ends[:,1]-ends[:,0]; d /= np.linalg.norm(d,axis=1)[:,None]
    axis = np.tile([0.,0.,1.],(len(d),1)); axis[np.abs(d[:,2])>.9] = [1.,0.,0.]
    n = np.cross(d,axis); n /= np.linalg.norm(n,axis=1)[:,None]
    v = np.cross(d,n); half = config['wire_diameter_m']/2
    a,b = ends[:,0],ends[:,1]
    solids = np.stack([a-n*half-v*half,b-n*half-v*half,b+n*half-v*half,a+n*half-v*half,
                       a-n*half+v*half,b-n*half+v*half,b+n*half+v*half,a+n*half+v*half],axis=1)
    net = {'vertices':solids.reshape(-1,3),'triangles':(FACES[None,:,:]+np.arange(len(solids))[:,None,None]*8).reshape(-1,3),
           'collision':False,'kind':'rockfall_net'}
    curbs=[];curb_probes=[];curb_joints=[]
    curb_samples=np.linspace(clo,chi,int(np.ceil((chi-clo)/config['section_step_m']))+1)
    sections=[]
    for s in curb_samples:
        edge=np.array([np.interp(s,samples,edges[:,j]) for j in range(2)])
        nn=np.array([np.interp(s,samples,normal[:,j]) for j in range(2)]);nn/=np.linalg.norm(nn)
        c=edge+nn*config['curb_center_offset_m'];gz=float(ground.sample(c)[0]);z=float(np.interp(s,samples,asphalt_z))
        sections.append({'center':c,'normal':nn,'bottom':min(z,gz)-config['curb_embed_m'],
                         'top':max(z+config['curb_exposure_m'],gz+.04)})
    for i,(a,b) in enumerate(zip(sections,sections[1:])):
        solid=joined_prism([a,b],config['curb_width_m']);curbs.append(solid)
        c=solid.mean(0);nn=a['normal']+b['normal'];nn/=np.linalg.norm(nn)
        curb_probes.append({'start_cm':((c+np.r_[nn*.5,0])*100).tolist(),
                            'end_cm':((c-np.r_[nn*.5,0])*100).tolist()})
        if i:curb_joints.append({'left_solid':i-1,'right_solid':i})
    curb={'vertices':np.asarray(curbs).reshape(-1,3),'triangles':np.concatenate([
        convex_faces(v)+i*8 for i,v in enumerate(curbs)]),'collision':True,'kind':'rockfall_curb'}
    records=[]; owner_tiles=set()
    for data in [net,curb]:
        # This observed run must stay in one native tile; splitting at a tile
        # boundary must be explicit rather than losing connected wire segments.
        vv=data['vertices']; owners=[t for t in old['tiles'] if np.all(
            (vv[:,0]*100>=t['bounds_xy_cm'][0])&(vv[:,0]*100<t['bounds_xy_cm'][2])&
            (vv[:,1]*100>=t['bounds_xy_cm'][1])&(vv[:,1]*100<t['bounds_xy_cm'][3]))]
        if len(owners)!=1:raise ValueError('Observed mesh requires explicit multi-tile splitting')
        tile=owners[0];owner_tiles.add(tile['id']);location=np.array([*tile['location_cm'][:2],0.])
        # A rotated 3 mm wire needs more transport precision than a curb.
        # Rounding centimetres to five places can move a tube corner 0.14 um
        # outside the supporting plane. Keep the independent convexity gate.
        local=np.round(vv*100-location,6 if data['kind']=='rockfall_net' else 5);name=data['kind']+'_'+tile['id']
        payload={'vertices_cm':local.tolist(),'triangles':data['triangles'].tolist(),'closed_surface':True}
        if data['collision']:payload['collision_convexes_cm']=local.reshape(-1,8,3).tolist()
        f=folder/(name+'.json');f.write_text(json.dumps(payload,separators=(',',':')))
        records.append({'id':name,'tile':tile['id'],'kind':data['kind'],'source':str(f),'sha256':sha(f),
            'asset':'/Game/World/Driving/F_'+build+'/Meshes/'+name,'location_cm':location.tolist(),
            'vertices':len(vv),'triangles':len(data['triangles']),'collision_enabled':data['collision'],
            'actor_tag':'RockfallEdge'})
    m=copy.deepcopy(old);m['build_id']=build;m['meshes']+=records
    for tile in m['tiles']:
        for key in ['structure_parent_map','rockfall_parent_map']:tile.pop(key,None)
        if tile['id'] in owner_tiles:
            tile['rockfall_parent_map']=tile['map'];tile['map']='/Game/World/Driving/F_'+build+'/Terrain/'+tile['id']
    m['report']={**m['report'],'build_id':build,'native_imported':False,'full_lap_driven':False}
    m['rockfall_edges']={'parent_build_id':old['build_id'],'parent_draft':str(parent),'parent_manifest':str(old_path),
        'input_sha256':fingerprints,'config':config,'records':records,'photo_projection':{'net':net_refs,'curb':curb_refs},
        'net_profile_station_range_m':[lo,hi],'curb_profile_station_range_m':[clo,chi],
        'net_hex_edges':len(param),'net_wire_pieces':len(ends),'net_wire_centerlines_cm':(ends*100).tolist(),
        'net_parametric_edges_m':uv.tolist(),'net_bank_sections':{'station_m':samples.tolist(),
        'asphalt_edge_UE_xy_m':edges.tolist(),'uphill_UE_xy_unit':normal.tolist()},
        'curb_collision_probes':curb_probes,'curb_shared_joints':curb_joints,
        'metric_dimensions_measured':False,'observed_real_world_ends_established':False,
        'all_source_context_reconstructed':False,'asphalt_or_height_bytes_changed':False}
    (folder/'manifest.json').write_text(json.dumps(m,indent=2))
    world=json.loads((parent/'circuit_driving_world.json').read_text());world['build_id']=build
    maps={t['id']:t['map'] for t in m['tiles']}
    for t in world['tiles']:t['map']=maps[t['id']]
    route=json.loads((parent/'circuit_itinerary.json').read_text());route['build_id']=build
    route['rockfall_parent_build_id']=old['build_id'];route['rockfall_variant_physically_verified']=False
    (draft/'circuit_driving_world.json').write_text(json.dumps(world))
    (draft/'circuit_itinerary.json').write_text(json.dumps(route))
    report={'build_id':build,'parent_build_id':old['build_id'],'manifest':str(folder/'manifest.json'),'draft':str(draft),
        'added_mesh_count':len(records),'net_hex_edges':len(param),'net_wire_pieces':len(ends),
        'curb_solids':len(curbs),'net_profile_length_m':hi-lo,'curb_profile_length_m':chi-clo,
        'asphalt_and_terrain_preserved':True,'activated':False}
    (draft/'structure_preparation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
