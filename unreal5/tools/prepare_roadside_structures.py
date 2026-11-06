"""Add observed anthropic structures in a separate derivative of a proven road.

The parent pavement, native heights and original maps are immutable. Placement
uses the actual asphalt boundary, source bank classification and explicit design
dimensions. Street View establishes the elements; dimensions are not surveyed.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
import shapely
from road_surface import RoadSurface
from prepare_reentry_checks import NativeGround
from roadside_joints import joined_prism,convex_faces
from observed_roadside_extent import clip_segment,terminal_side,rounded_terminal,frame

ROOT=Path(__file__).resolve().parents[1]
FACES=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],
                [1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prism(a,b,width,bottom,top):
    d=b-a;normal=np.array([-d[1],d[0]])/np.linalg.norm(d)
    footprint=np.array([a-normal*width/2,b-normal*width/2,b+normal*width/2,a+normal*width/2])
    return np.vstack([np.column_stack([footprint,[bottom[0],bottom[1],bottom[1],bottom[0]]]),
                      np.column_stack([footprint,[top[0],top[1],top[1],top[0]]])])


def points(geometry):
    if geometry.is_empty:return []
    if geometry.geom_type=='Point':return [np.asarray(geometry.coords[0])]
    if hasattr(geometry,'geoms'):return [p for g in geometry.geoms for p in points(g)]
    return [np.asarray(v) for v in geometry.coords]


def boundary_point(center,direction,footprint):
    ray=shapely.LineString([center,center+direction*12])
    hits=points(ray.intersection(footprint.boundary))
    valid=[p for p in hits if np.dot(p-center,direction)>.05]
    if not valid:raise ValueError('Observed edge has no local asphalt boundary')
    return min(valid,key=lambda p:np.dot(p-center,direction))


def main():
    p=argparse.ArgumentParser();p.add_argument('--parent-draft',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True);args=p.parse_args()
    parent=args.parent_draft.resolve();parent_world=parent/'circuit_driving_world.json'
    world=json.loads(parent_world.read_text());parent_id=world['build_id']
    parent_import=json.loads((parent/'import_report.json').read_text())
    if not parent_import['all_imported'] or parent_import['build_id']!=parent_id:raise RuntimeError('Imported parent required')
    manifest_path=Path(parent_import['manifest'])
    original=json.loads(manifest_path.read_text());config=json.loads(args.config.read_text())
    fingerprints={str(path.resolve()):sha(path) for path in [manifest_path,parent_world,args.config,
        parent/'circuit_itinerary.json',Path(__file__),ROOT/'tools/road_surface.py',ROOT/'tools/prepare_reentry_checks.py',
        ROOT/'Unreal/Source/SoffumbergoTerrainEditor/CircuitMesh.cpp',ROOT/'tools/roadside_joints.py',
        ROOT/'tools/import_roadside_structures.py',ROOT/'tools/audit_roadside_structures.py',ROOT/'tools/observed_roadside_extent.py']}
    for name in config['source_reviews']:
        path=ROOT/name;fingerprints[str(path)]=sha(path)
    build=hashlib.sha256(json.dumps(fingerprints,sort_keys=True).encode()).hexdigest()[:12]
    folder=ROOT/'terrain/road_structures'/build;draft=ROOT/'results/road_drafts'/build
    if folder.exists() or draft.exists():raise RuntimeError('Preserve earlier structure draft')
    folder.mkdir(parents=True);draft.mkdir(parents=True)
    surface=RoadSurface(original)
    raw=NativeGround(json.loads((ROOT/'terrain/world_tiles/manifest.json').read_text()))
    derived=NativeGround(original)
    profile=np.asarray(original['profile_UE_cm'])/100;station=np.asarray(original['profile_station_m'])
    tangents=np.diff(profile[:,:2],axis=0);tangents/=np.linalg.norm(tangents,axis=1)[:,None]
    node_tangents=np.vstack([tangents[0],tangents[:-1]+tangents[1:],tangents[-1]])
    reversing=np.linalg.norm(node_tangents,axis=1)<1.e-8
    node_tangents[reversing]=np.vstack([tangents,tangents[-1]])[reversing]
    node_tangents/=np.linalg.norm(node_tangents,axis=1)[:,None]
    gathered={};probes=[];reviews=[];discarded=[];seen=set();joint_ends={};terminals=[];extent_omitted=[]
    def add(control,kind,vertices,probe,joints=None):
        xy=vertices[:4,:2];poly=shapely.Polygon(xy)
        # Structures project entirely beyond asphalt, including end caps.
        if poly.intersects(footprint.buffer(config['minimum_asphalt_clearance_m'])):
            discarded.append({'control':control['id'],'kind':kind,'reason':'plan intrusion into protected asphalt',
                              'center_UE_xy_m':vertices[:4,:2].mean(axis=0).tolist()});return False
        center=vertices.mean(axis=0)
        owner=next(t for t in original['tiles'] if t['bounds_xy_cm'][0]<=center[0]*100<t['bounds_xy_cm'][2]
                   and t['bounds_xy_cm'][1]<=center[1]*100<t['bounds_xy_cm'][3])
        key=(control['id'],owner['id'],kind)
        data=gathered.setdefault(key,{'vertices':[],'triangles':[]})
        faces=convex_faces(vertices) if config.get('continuous_joints') else FACES
        offset=len(data['vertices']);data['triangles'].extend((faces+offset).tolist());data['vertices'].extend(vertices.tolist())
        if joints:
            for end,token in enumerate(joints):
                joint_ends.setdefault(token,[]).append({'mesh_key':list(key),'vertex_indices':
                    [offset+j for j in ([0,3,4,7] if end==0 else [1,2,5,6])]})
        probes.append({'mesh_key':list(key),'start_cm':(np.asarray(probe[0])*100).tolist(),
                       'end_cm':(np.asarray(probe[1])*100).tolist()})
        return True
    for control in config['controls']:
        anchor=np.asarray(control['center_UE_xy_m']);radius=control['review_radius_m']
        region=shapely.Point(anchor).buffer(radius)
        ids=surface.tree.query(shapely.box(
            (anchor[0]-radius-15)*100,(anchor[1]-radius-15)*100,
            (anchor[0]+radius+15)*100,(anchor[1]+radius+15)*100),predicate='intersects')
        footprint=shapely.union_all(surface.polygons[ids])
        footprint=shapely.transform(footprint,lambda q:q/100)
        accepted_before=len(probes);samples=[]
        section_cache={};terminal_cache={}
        for i,(pa,pb) in enumerate(zip(profile[:-1],profile[1:])):
            a,b=pa[:2],pb[:2]
            if shapely.LineString([a,b]).distance(shapely.Point(anchor))>radius:continue
            direction=(b-a)/np.linalg.norm(b-a);normal=np.array([-direction[1],direction[0]])
            count=max(1,int(np.ceil(np.linalg.norm(b-a)/config['maximum_segment_m'])))
            for k in range(count):
                q0=a+(b-a)*k/count;q1=a+(b-a)*(k+1)/count;mid=(q0+q1)/2
                if np.linalg.norm(mid-anchor)>radius:continue
                token=(control['id'],*sorted([tuple(np.round(q0,4)),tuple(np.round(q1,4))]))
                if token in seen:continue
                seen.add(token)
                h=raw.sample(np.array([mid+normal*5,mid-normal*5]))
                if not np.isfinite(h).all():raise ValueError('Missing native bank samples')
                downhill=normal if h[0]<h[1] else -normal
                original_q0,original_q1=q0.copy(),q1.copy()
                for kind,side in [('guardrail',downhill)]+([('wall',downhill if control['wall']=='downhill' else -downhill)] if control.get('wall') else []):
                    q0,q1=original_q0.copy(),original_q1.copy()
                    extent=control.get('guardrail_extent') if kind=='guardrail' else None
                    if extent:
                        clipped=clip_segment(q0,q1,extent)
                        if clipped is None:
                            extent_omitted.append({'control':control['id'],'profile_index':i,'from_UE_xy_m':q0.tolist(),'to_UE_xy_m':q1.tolist()})
                            continue
                        q0,q1=clipped
                    edge=np.array([boundary_point(q,side,footprint) for q in [q0,q1]])
                    # Surface heights are evaluated on the exact boundary, not
                    # by extrapolating a nearest triangle beyond the road.
                    height,dist=surface.sample(edge*100);height/=100
                    if dist.max()>.01:raise ValueError('Boundary height is outside asphalt')
                    centerline=edge+side*config['edge_offset_m']
                    d=centerline[1]-centerline[0]
                    if np.linalg.norm(d)<(1.e-6 if extent else .05):continue
                    out=side*.35
                    sections=[];joint_tokens=[]
                    if config.get('continuous_joints'):
                        sign=1 if np.dot(side,normal)>0 else -1
                        fractions=[float(np.dot(q-a,b-a)/np.dot(b-a,b-a)) for q in [q0,q1]] if extent else [k/count,(k+1)/count]
                        for q,fraction in zip([q0,q1],fractions):
                            token=(control['id'],kind,sign,*np.round(q,6));joint_tokens.append(token)
                            if token not in section_cache:
                                tangent=(1-fraction)*node_tangents[i]+fraction*node_tangents[i+1]
                                tangent/=np.linalg.norm(tangent);n=sign*np.array([-tangent[1],tangent[0]])
                                edge_point=boundary_point(q,n,footprint);z,dist=surface.sample(edge_point*100)
                                if dist[0]>.01:raise ValueError('Joint outside asphalt edge')
                                offset=config.get('wall_edge_offset_m',config['edge_offset_m']) if kind=='wall' else config['edge_offset_m']
                                z=float(z[0]/100);c=edge_point+n*offset
                                bank=float(raw.sample(c)[0]);foundation=float(derived.sample(c)[0])
                                if not np.isfinite([bank,foundation]).all():raise ValueError('Missing joint foundation')
                                if kind=='guardrail':
                                    low=z+config['guardrail_beam_center_m']-config['guardrail_beam_height_m']/2
                                    high=low+config['guardrail_beam_height_m']
                                elif control['wall']=='downhill':
                                    low=min(bank,foundation)-config['wall_foundation_embed_m'];high=z-.04
                                    low=min(low,high-config['wall_minimum_height_m'])
                                else:
                                    low=min(z,foundation)-config['wall_foundation_embed_m']
                                    high=max(z+config['uphill_wall_minimum_exposure_m'],min(bank+.04,z+config['uphill_wall_maximum_height_m']))
                                section_cache[token]={'center':c,'normal':n,'bottom':low,'top':high,'height':z}
                            sections.append(section_cache[token])
                        centerline=np.asarray([s['center'] for s in sections]);height=np.asarray([s['height'] for s in sections]);d=centerline[1]-centerline[0]
                    if kind=='guardrail':
                        bottom=height+config['guardrail_beam_center_m']-config['guardrail_beam_height_m']/2
                        top=bottom+config['guardrail_beam_height_m']
                        v=joined_prism(sections,config['guardrail_beam_width_m']) if sections else prism(*centerline,config['guardrail_beam_width_m'],bottom,top)
                        z=float((bottom.mean()+top.mean())/2);c=centerline.mean(axis=0)
                        if add(control,'metal',v,([*list(c-out),z],[*list(c+out),z]),joint_tokens):
                            samples.append({'kind':'guardrail','edge_UE_xy_m':edge.mean(axis=0).tolist()})
                            if extent:
                                for q,section,joint in zip([q0,q1],sections,joint_tokens):
                                    end=terminal_side(q,extent)
                                    if end is not None:
                                        local_axis=d/np.linalg.norm(d)
                                        if np.dot(local_axis,frame(extent)[1])<0:local_axis=-local_axis
                                        terminal_cache[joint]={'section':section,'open_direction':end*local_axis,'joint':joint,'axis_point':q}
                        s0=station[i]+np.linalg.norm(q0-a);s1=station[i]+np.linalg.norm(q1-a)
                        pitch=config['guardrail_post_spacing_m']
                        for mark in np.arange(np.ceil(s0/pitch)*pitch,s1+1.e-7,pitch):
                            t=(mark-s0)/max(s1-s0,1.e-9);c=centerline[0]+t*d;z=float(height[0]+t*(height[1]-height[0]))
                            tangent=d/np.linalg.norm(d);half=tangent*config['guardrail_post_width_m']/2
                            ground=float(derived.sample(c)[0])
                            if not np.isfinite(ground):raise ValueError('Guardrail post has no native foundation')
                            base=min(z-.2,ground-.2)
                            v=prism(c-half,c+half,config['guardrail_post_width_m'],[base]*2,[z+config['guardrail_post_height_m']]*2)
                            add(control,'metal',v,([*list(c-out),z+.3],[*list(c+out),z+.3]))
                    else:
                        bank=raw.sample(centerline)
                        if not np.isfinite(bank).all():raise ValueError('Missing wall foundation source')
                        if control['wall']=='downhill':
                            bottom=bank-config['wall_foundation_embed_m'];top=height-.04
                        else:
                            bottom=height-config['wall_foundation_embed_m']
                            top=np.minimum(bank+.04,height+config['uphill_wall_maximum_height_m'])
                        if not sections and np.min(top-bottom)<config['wall_minimum_height_m']:continue
                        if sections:
                            bottom=np.asarray([s['bottom'] for s in sections]);top=np.asarray([s['top'] for s in sections])
                        v=joined_prism(sections,config['wall_thickness_m']) if sections else prism(*centerline,config['wall_thickness_m'],bottom,top)
                        z=float((bottom.mean()+top.mean())/2);c=centerline.mean(axis=0)
                        add(control,'concrete',v,([*list(c-out),z],[*list(c+out),z]),joint_tokens)
        for terminal in terminal_cache.values():
            extent=control['guardrail_extent'];length=extent['terminal_nose_length_m']
            chain=rounded_terminal(terminal['section'],terminal['open_direction'],length,extent['terminal_nose_segments'])
            previous=terminal['joint'];accepted=0
            for j,(left,right) in enumerate(zip(chain[:-1],chain[1:])):
                token=(control['id'],'terminal',*np.round(terminal['axis_point'],6),j)
                v=joined_prism([left,right],config['guardrail_beam_width_m'])
                c=v.mean(axis=0);out=terminal['section']['normal']*.35
                if not add(control,'metal',v,([*list(c[:2]-out),c[2]],[*list(c[:2]+out),c[2]]),[previous,token]):
                    raise RuntimeError('Observed terminal infringes protected asphalt')
                previous=token;accepted+=1
            terminals.append({'control':control['id'],'axis_point_UE_xy_m':terminal['axis_point'].tolist(),
                'rail_center_UE_xy_m':terminal['section']['center'].tolist(),'open_UE_xy_unit':terminal['open_direction'].tolist(),
                'engineering_nose_length_m':length,'convex_loft_solids':accepted,
                'placement_status':'Observed terminal/open-approach topology; metric station and nose dimensions are explicit engineering choices.'})
        reviews.append({'id':control['id'],'observed_guardrail':True,'observed_wall_side':control.get('wall'),
                        'generated_solid_count':len(probes)-accepted_before,'engineering_review_radius_m':radius,
                        'physical_and_visual_review_complete':False})
    if not gathered:raise RuntimeError('No roadside geometry generated')
    records=[];mesh_names={};quantized_hulls=[]
    for (control,tile,kind),geometry in gathered.items():
        name='Roadside_'+control+'_'+tile+'_'+kind
        owner=next(t for t in original['tiles'] if t['id']==tile)
        location=np.asarray([*owner['location_cm'][:2],0]);vertices=np.asarray(geometry['vertices'])*100-location
        local=np.round(vertices,5)
        triangles=np.asarray(geometry['triangles'],int)
        for j,solid in enumerate(local.reshape(-1,8,3)/100):
            faces=solid[triangles[j*12:j*12+12]-j*8]
            normal=np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0])
            distance=np.einsum('fvi,fi->fv',solid[None,:,:]-faces[:,0,None,:],normal)
            if (distance.max(axis=1)>1.e-7*np.linalg.norm(normal,axis=1)).any():
                # Quantization can change the supporting diagonal of a very
                # small curved terminal face. Use its actual saved hull.
                triangles[j*12:j*12+12]=convex_faces(solid)+j*8
                quantized_hulls.append({'mesh_id':name,'solid_index':j})
        data={'vertices_cm':local.tolist(),'triangles':triangles.tolist(),
              'collision_convexes_cm':local.reshape(-1,8,3).tolist()}
        path=folder/(name+'.json');path.write_text(json.dumps(data,separators=(',',':')))
        asset='/Game/World/Driving/S_'+build+'/Meshes/'+name
        records.append({'id':name,'tile':tile,'kind':kind,'source':str(path),'sha256':sha(path),'asset':asset,
                        'location_cm':location.tolist(),'vertices':len(vertices),'triangles':len(geometry['triangles']),
                        'actor_tag':'RoadsideStructure','observed_control':control})
        mesh_names[(control,tile,kind)]=name
    for probe in probes:probe['mesh_id']=mesh_names[tuple(probe.pop('mesh_key'))]
    # Previously observed openings remain binding in later derivatives. They
    # cannot be rediscovered only from removed beams once those beams are gone.
    open_probes=copy.deepcopy(original.get('roadside_structures',{}).get('open_collision_probes',[]))
    for control in config['controls']:
        extent=control.get('guardrail_extent')
        if not extent:continue
        origin,axis=frame(extent)
        for old in original.get('roadside_structures',{}).get('records',[]):
            if old['observed_control']!=control['id'] or old['kind']!='metal':continue
            data=json.loads(Path(old['source']).read_text())
            solids=(np.asarray(data['vertices_cm'])+old['location_cm']).reshape(-1,8,3)/100
            for solid in solids:
                if np.linalg.norm(solid[1,:2]-solid[0,:2])<.4:continue
                center=solid.mean(axis=0);forward=float((center[:2]-origin)@axis)
                outside=(extent.get('minimum_forward_m') is not None and forward<extent['minimum_forward_m']-3) or (extent.get('maximum_forward_m') is not None and forward>extent['maximum_forward_m']+3)
                if not outside:continue
                tangent=solid[1,:2]-solid[0,:2];normal=np.array([-tangent[1],tangent[0]])/np.linalg.norm(tangent)
                open_probes.append({'control':control['id'],'mesh_id':old['id'],'tile':old['tile'],
                    'start_cm':((center+np.r_[normal*.35,0])*100).tolist(),
                    'end_cm':((center-np.r_[normal*.35,0])*100).tolist(),
                    'expected':'No hit on replacement guardrail in the observed open approach'})
    # New observed runs also need absence evidence beyond their ends, even
    # where no parent beam ever existed. Derive rays from the same asphalt edge.
    controls_by_id={c['id']:c for c in config['controls']}
    for omitted in extent_omitted:
        control=controls_by_id[omitted['control']];extent=control['guardrail_extent']
        a=np.asarray(omitted['from_UE_xy_m']);b=np.asarray(omitted['to_UE_xy_m']);mid=(a+b)/2
        origin,axis=frame(extent);forward=float((mid-origin)@axis)
        if not ((extent.get('minimum_forward_m') is not None and forward<extent['minimum_forward_m']-3)
                or (extent.get('maximum_forward_m') is not None and forward>extent['maximum_forward_m']+3)):continue
        tangent=(b-a)/np.linalg.norm(b-a);normal=np.array([-tangent[1],tangent[0]])
        h=raw.sample(np.array([mid+normal*5,mid-normal*5]))
        if not np.isfinite(h).all():raise ValueError('Missing observed open-approach ground')
        side=normal if h[0]<h[1] else -normal
        ids=surface.tree.query(shapely.box(*list(mid*100-1200),*list(mid*100+1200)),predicate='intersects')
        footprint=shapely.transform(shapely.union_all(surface.polygons[ids]),lambda q:q/100)
        edge=boundary_point(mid,side,footprint);height,distance=surface.sample(edge*100)
        if distance[0]>.01:raise ValueError('Absence probe outside actual asphalt edge')
        c=edge+side*config['edge_offset_m'];z=float(height[0]/100+config['guardrail_beam_center_m'])
        owner=next(t for t in original['tiles'] if t['bounds_xy_cm'][0]<=c[0]*100<t['bounds_xy_cm'][2]
                   and t['bounds_xy_cm'][1]<=c[1]*100<t['bounds_xy_cm'][3])
        target=mesh_names.get((control['id'],owner['id'],'metal'))
        if target is None:continue
        open_probes.append({'control':control['id'],'mesh_id':target,'tile':owner['id'],
            'start_cm':(np.r_[c-side*.35,z]*100).tolist(),'end_cm':(np.r_[c+side*.35,z]*100).tolist(),
            'expected':'No hit on this guardrail beyond its observed terminal',
            'method':'Hypothetical beam-center ray on omitted road interval; no parent beam required'})
    unique_open={}
    for probe in open_probes:
        key=(probe['control'],probe['mesh_id'],*np.round(probe['start_cm'],3),*np.round(probe['end_cm'],3))
        unique_open[key]=probe
    open_probes=list(unique_open.values())
    joins=[]
    for token,ends in joint_ends.items():
        if len(ends)<2:continue
        for end in ends:end['mesh_id']=mesh_names[tuple(end.pop('mesh_key'))]
        joins.append({'token':list(token),'ends':ends})
    manifest=copy.deepcopy(original);manifest['build_id']=build
    replaced=original.get('roadside_structures',{}).get('records',[])
    if replaced and not config.get('continuous_joints'):raise RuntimeError('Replacement requires explicit continuous-joint mode')
    replaced_ids={r['id'] for r in replaced}
    manifest['meshes']=[r for r in manifest['meshes'] if r['id'] not in replaced_ids]
    changed_tiles={r['tile'] for r in records}
    for tile in manifest['tiles']:
        tile.pop('structure_parent_map',None)
        if tile['id'] in changed_tiles:
            tile['structure_parent_map']=tile['map'];tile['map']='/Game/World/Driving/S_'+build+'/Terrain/'+tile['id']
    maps={t['id']:t['map'] for t in manifest['tiles']}
    for tile in world['tiles']:tile['map']=maps[tile['id']]
    world['build_id']=build
    manifest['meshes']+=records
    manifest['report']={**manifest['report'],'build_id':build,'native_imported':False,'full_lap_driven':False}
    manifest['roadside_structures']={'parent_build_id':parent_id,'parent_manifest':str(manifest_path),'parent_draft':str(parent),
        'replaced_mesh_ids':sorted(replaced_ids),'shared_cross_section_joints':joins,
        'observed_terminals':terminals,'observed_open_intervals_omitted':extent_omitted,
        'open_collision_probes':open_probes,
        'native_precision_hull_retriangulations':quantized_hulls,
        'input_sha256':fingerprints,'config':config,'records':records,'collision_probes':probes,'controls':reviews,
        'asphalt_or_native_height_bytes_changed':False,'discarded_intruding_solids':discarded,
        'placement_status':'Observed anthropic elements; engineering dimensions and local extents, pending native collision and visual review',
        'all_observed_roadside_elements_complete':False}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (draft/'circuit_driving_world.json').write_text(json.dumps(world))
    itinerary=json.loads((parent/'circuit_itinerary.json').read_text());itinerary['build_id']=build
    itinerary['structure_parent_build_id']=parent_id;itinerary['structure_variant_physically_verified']=False
    (draft/'circuit_itinerary.json').write_text(json.dumps(itinerary))
    report={'build_id':build,'parent_build_id':parent_id,'manifest':str(folder/'manifest.json'),'draft':str(draft),
            'mesh_count':len(records),'solid_count':len(probes),'discarded_intrusions':len(discarded),
            'asphalt_and_terrain_preserved':True,'activated':False,'controls':reviews}
    (draft/'structure_preparation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
