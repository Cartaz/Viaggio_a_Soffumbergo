"""Query the exact generated asphalt triangles in Unreal geographic centimeters."""
import json
from pathlib import Path
import numpy as np
import shapely

class RoadSurface:
    def __init__(self, manifest, include_shoulders=False):
        chunks=[]
        self.meshes=manifest['meshes']
        for item in self.meshes:
            if item['kind'] not in (['asphalt','shoulder'] if include_shoulders else ['asphalt']):continue
            data=json.loads(Path(item['source']).read_text())
            v=np.asarray(data['vertices_cm'])+np.asarray(item['location_cm'])
            chunks.append(v[np.asarray(data['triangles'])])
        self.faces=np.concatenate(chunks)
        self.xy=self.faces[:,:,:2]
        self.polygons=shapely.polygons(self.xy)
        self.tree=shapely.STRtree(self.polygons)

    def sample(self, positions, *, clamp_to_triangle=False):
        p=np.atleast_2d(positions).astype(float)
        pairs,d=self.tree.query_nearest(shapely.points(p),all_matches=False,return_distance=True)
        order=np.empty(len(p),int);distance=np.empty(len(p));order[pairs[0]]=pairs[1];distance[pairs[0]]=d
        tri=self.xy[order];a=tri[:,0];ab=tri[:,1]-a;ac=tri[:,2]-a;q=p-a
        den=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
        u=(q[:,0]*ac[:,1]-q[:,1]*ac[:,0])/den
        v=(ab[:,0]*q[:,1]-ab[:,1]*q[:,0])/den
        if clamp_to_triangle:
            outside=(u<0)|(v<0)|(u+v>1)
            ids=np.flatnonzero(outside)
            if len(ids):
                aa=tri[ids];dd=np.roll(aa,-1,axis=1)-aa
                frac=np.clip(((p[ids,None]-aa)*dd).sum(2)/(dd*dd).sum(2),0,1)
                nearest=aa+frac[:,:,None]*dd
                edge=np.argmin(((nearest-p[ids,None])**2).sum(2),axis=1)
                q[ids]=nearest[np.arange(len(ids)),edge]-a[ids]
                u[ids]=(q[ids,0]*ac[ids,1]-q[ids,1]*ac[ids,0])/den[ids]
                v[ids]=(ab[ids,0]*q[ids,1]-ab[ids,1]*q[ids,0])/den[ids]
        z=self.faces[order,:,2]
        return z[:,0]+u*(z[:,1]-z[:,0])+v*(z[:,2]-z[:,0]),distance

    def local_drivable_polygon(self, center_cm, radius_m):
        bounds=shapely.box(center_cm[0]-radius_m*100,center_cm[1]-radius_m*100,
                           center_cm[0]+radius_m*100,center_cm[1]+radius_m*100)
        polys=[]
        for item in self.meshes:
            if item['kind'] not in ['asphalt','shoulder']:continue
            data=json.loads(Path(item['source']).read_text())
            v=np.asarray(data['vertices_cm'])+np.asarray(item['location_cm'])
            if v[:,0].max()<bounds.bounds[0] or v[:,0].min()>bounds.bounds[2] or v[:,1].max()<bounds.bounds[1] or v[:,1].min()>bounds.bounds[3]:continue
            triangles=shapely.polygons(v[np.asarray(data['triangles']),:2])
            ids=shapely.intersects(triangles,bounds)
            polys.extend(triangles[ids])
        return shapely.union_all(polys).intersection(bounds)
