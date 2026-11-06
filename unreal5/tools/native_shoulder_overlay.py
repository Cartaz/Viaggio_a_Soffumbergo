"""Earth overlay conforming to the exact native Landscape grid triangles.

The existing shoulder footprint, including bridge exclusions, is preserved.
Only the narrow asphalt seam blends heights; elsewhere the overlay sits 2 cm
above the existing native terrain instead of spanning it with coarse triangles.
"""
import json
from pathlib import Path
import numpy as np
import shapely


def overlay(tile, old_record, ground, road, seam_width_m=.15):
    old=json.loads(Path(old_record['source']).read_text())
    old_v=(np.asarray(old['vertices_cm'])+old_record['location_cm'])/100
    footprint=shapely.union_all(shapely.polygons(old_v[np.asarray(old['triangles']),:2]))
    x0,y0,x1,y1=np.asarray(tile['bounds_xy_cm'])/100
    step=tile['xy_scale_cm']/100;n=tile['samples']-1
    bx0,by0,bx1,by1=footprint.bounds
    ix=np.arange(max(0,int(np.floor((bx0-x0)/step))),min(n,int(np.ceil((bx1-x0)/step))))
    iy=np.arange(max(0,int(np.floor((by0-y0)/step))),min(n,int(np.ceil((by1-y0)/step))))
    xx,yy=np.meshgrid(x0+(ix+.5)*step,y0+(iy+.5)*step)
    near=shapely.contains_xy(footprint.buffer(step/np.sqrt(2)+1.e-6),xx,yy)
    centers=np.column_stack([xx[near],yy[near]])
    raster=np.fromfile(tile['heightmap'],'<u2').reshape(n+1,n+1)
    holes=np.fromfile(tile['holes'],'u1').reshape(n+1,n+1)
    ci=np.floor((centers[:,0]-x0)/step).astype(int);ri=np.floor((centers[:,1]-y0)/step).astype(int)
    visible=(holes[ri,ci]==0)&(holes[ri,ci+1]==0)&(holes[ri+1,ci]==0)&(holes[ri+1,ci+1]==0)
    omitted_cells=int(np.count_nonzero(~visible));centers=centers[visible]
    corners=centers[:,None,:]+step*np.array([[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]]])
    native_faces=corners[:,[[0,1,2],[0,2,3]],:].reshape(-1,3,2)
    clipped=shapely.intersection(shapely.polygons(native_faces),footprint)
    parts=shapely.get_parts(clipped)
    parts=parts[(shapely.get_type_id(parts)==3)&(shapely.area(parts)>1.e-12)]
    triangles=shapely.get_parts(shapely.constrained_delaunay_triangles(parts))
    triangles=triangles[shapely.area(triangles)>1.e-12]
    faces=shapely.get_coordinates(triangles).reshape(-1,4,2)[:,:3]
    xy,inverse=np.unique(np.round(faces.reshape(-1,2),6),axis=0,return_inverse=True)
    tri=inverse.reshape(-1,3)
    # Visibility was checked for the producing native cell. A shared corner is
    # still valid when an adjacent cell is masked; don't reject it by querying
    # the half-open neighboring cell a second time.
    q=(xy-[x0,y0])/step;cell=np.minimum(np.floor(q).astype(int),n-1);fraction=q-cell
    ix,iy=cell.T;fx,fy=fraction.T
    a=raster[iy,ix].astype(float);b=raster[iy,ix+1].astype(float)
    c=raster[iy+1,ix].astype(float);d=raster[iy+1,ix+1].astype(float)
    g=np.where(fx>=fy,a+(b-a)*fx+(d-b)*fy,a+(d-c)*fx+(c-a)*fy)*ground.quant+ground.zero
    edge,distance=road.sample(xy*100,clamp_to_triangle=True);edge/=100;distance/=100
    # Every distant vertex is on its original native triangle. Seam correction
    # vanishes before the overlay reaches a steep source bank.
    blend=np.clip(distance/seam_width_m,0,1);blend=blend*blend*(3-2*blend)
    height=edge*(1-blend)+(g+.02)*blend
    valid=np.isfinite(height[tri]).all(axis=1)
    omitted=int(np.count_nonzero(~valid));tri=tri[valid]
    used,renumber=np.unique(tri,return_inverse=True);tri=renumber.reshape(-1,3)
    vertices=np.column_stack([xy[used],height[used]])
    # Upward winding in Unreal's east/south/up axes, matching existing surfaces.
    a=vertices[tri];cross=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0])[:,2]
    collapsed=np.abs(cross)<1.e-12
    removed_area=shapely.area(triangles)[valid][collapsed]
    if len(removed_area) and removed_area.max()>step*2.e-6:
        raise RuntimeError('Collapsed overlay face exceeds coordinate-precision area bound')
    tri=tri[~collapsed];cross=cross[~collapsed]
    flip=cross<0;tri[flip]=tri[flip][:,[0,2,1]]
    diagnostic={'native_grid_step_m':step,'seam_blend_width_m':seam_width_m,
        'native_surface_offset_m':.02,'old_faces':len(old['triangles']),'new_faces':len(tri),
        'faces_touching_missing_native_cells_omitted':omitted,'old_planar_area_m2':float(footprint.area),
        'masked_native_cells_excluded_before_clipping':omitted_cells,
        'collapsed_boundary_faces_removed':int(collapsed.sum()),
        'prequantization_area_of_collapsed_faces_m2':float(removed_area.sum()),
        'new_planar_area_m2':float(shapely.area(shapely.polygons(vertices[tri,:2])).sum())}
    return vertices,tri,diagnostic
