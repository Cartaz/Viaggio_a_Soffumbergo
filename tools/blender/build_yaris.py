"""Build the MY22 Italian Trend study as real, editable geometry, not image planes.

Blender 4.5.3: --background --factory-startup --python tools/blender/build_yaris.py
Optional arguments after --: --render, --overwrite.
All secondary contours are photographic estimates. See references/yaris_2022.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "art/vehicles/yaris_2022"
SOURCE = ROOT / "art/source/yaris_2022"
TEX = OUT / "textures"
REPORT = ROOT / "reports/yaris_2022"
PI = math.pi
TAU = math.tau
CAR = None
GROUP = None
M = {}


def mat(name, color, rough=.5, metal=0, coat=0, emission=0, alpha=1):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, alpha)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, alpha)
    p.inputs["Alpha"].default_value = alpha
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Coat Weight"].default_value = coat
    p.inputs["Coat Roughness"].default_value = .17
    if emission:
        p.inputs["Emission Color"].default_value = (*color, 1)
        p.inputs["Emission Strength"].default_value = emission
    if alpha < 1:
        m.surface_render_method = "DITHERED"
    return m


def texmat(name, file, rough=.6, emissive=False):
    m = mat(name, (1, 1, 1), rough)
    n = m.node_tree.nodes.new("ShaderNodeTexImage")
    n.image = bpy.data.images.load(str(TEX / file))
    n.image.pack()
    p = m.node_tree.nodes.get("Principled BSDF")
    m.node_tree.links.new(n.outputs["Color"], p.inputs["Base Color"])
    if emissive:
        m.node_tree.links.new(n.outputs["Color"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = .25
    return m


def empty(name, at=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.location = at
    o.parent = parent
    return o


def register(o, name, material, parent=None):
    o.name = name
    o.data.materials.append(material)
    # Keep authored coordinates in vehicle space; pivots have their own origins.
    bpy.context.view_layer.update()
    world = o.matrix_world.copy()
    o.parent = parent or GROUP
    o.matrix_world = world
    return o


def mesh(name, verts, faces, material, smooth=True, parent=None, uv=None):
    d = bpy.data.meshes.new(name)
    d.from_pydata(verts, [], faces)
    d.update()
    bm = bmesh.new()
    bm.from_mesh(d)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(d)
    bm.free()
    o = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(o)
    register(o, name, material, parent)
    for f in d.polygons:
        f.use_smooth = smooth
    layer = d.uv_layers.new(name="UVMap")
    for face in d.polygons:
        for li in face.loop_indices:
            vi = d.loops[li].vertex_index
            if uv:
                layer.data[li].uv = uv[vi]
            else:
                p = verts[vi]
                layer.data[li].uv = (p[0] * 8, (p[1] + p[2]) * 8)
    return o


def box(name, size, at, material, bevel=.015, rotation=None, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=at)
    o = bpy.context.object
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rotation:
        o.rotation_euler = rotation
    register(o, name, material, parent)
    if bevel:
        b = o.modifiers.new("Edge radii", "BEVEL")
        b.width = bevel
        b.segments = 3
        o.modifiers.new("Corner normals", "WEIGHTED_NORMAL")
    return o


def ell(name, size, at, material, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=at)
    o = bpy.context.object
    o.scale = size
    register(o, name, material, parent)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def tube(name, points, radius, material, closed=False, sides=8, parent=None):
    # Parallel transported local frames avoid twisted cross sections on curved trim.
    points = [Vector(p) for p in points]
    verts, faces = [], []
    for i, p in enumerate(points):
        prev = points[(i - 1) % len(points)] if closed or i else p
        nxt = points[(i + 1) % len(points)] if closed or i < len(points) - 1 else p
        t = (nxt - prev).normalized()
        n = t.cross(Vector((0, 0, 1)))
        if n.length < .01:
            n = t.cross(Vector((0, 1, 0)))
        n.normalize()
        b = t.cross(n).normalized()
        for k in range(sides):
            a = TAU * k / sides
            verts.append(tuple(p + radius * (n * math.cos(a) + b * math.sin(a))))
    for i in range(len(points) if closed else len(points) - 1):
        j = (i + 1) % len(points)
        for k in range(sides):
            q = (k + 1) % sides
            faces.append((i * sides + k, i * sides + q, j * sides + q, j * sides + k))
    if not closed:
        faces += [tuple(reversed(range(sides))), tuple((len(points) - 1) * sides + k for k in range(sides))]
    return mesh(name, verts, faces, material, parent=parent)


def rod(name, a, b, radius, material, parent=None, vertices=24):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=(b - a).length, location=(a + b) / 2)
    o = bpy.context.object
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = (b - a).to_track_quat("Z", "Y")
    register(o, name, material, parent)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def panel(name, points, material, thick=.006, bevel=.005, parent=None):
    o = mesh(name, points, [tuple(range(len(points)))], material, smooth=False, parent=parent)
    if thick:
        m = o.modifiers.new("Panel thickness", "SOLIDIFY")
        m.thickness = thick
    if bevel:
        m = o.modifiers.new("Panel edge", "BEVEL")
        m.width = bevel
        m.segments = 3
        o.modifiers.new("Panel normals", "WEIGHTED_NORMAL")
    return o


def grid(name, fn, nu, nv, material, parent=None):
    vertices, faces, uv = [], [], []
    for i in range(nu + 1):
        for j in range(nv + 1):
            vertices.append(fn(i / nu, j / nv))
            uv.append((j / nv, i / nu))
    for i in range(nu):
        for j in range(nv):
            a = i * (nv + 1) + j
            faces.append((a, a + 1, a + nv + 2, a + nv + 1))
    return mesh(name, vertices, faces, material, parent=parent, uv=uv)


def lerp(a, b, t):
    return a + (b - a) * t


def sample(rows, y, index):
    for a, b in zip(rows, rows[1:]):
        if a[0] <= y <= b[0]:
            return lerp(a[index], b[index], (y - a[0]) / (b[0] - a[0]))
    return rows[0][index] if y < rows[0][0] else rows[-1][index]


# Hand traced silhouette stations, in metres: y, halfwidth at belt, belt height.
BODY = [(-1.87, .70, .86), (-1.72, .82, .94), (-1.47, .866, 1.005),
        (-1.20, .8725, 1.035), (-.75, .837, 1.015), (-.3, .814, .995),
        (.3, .805, .985), (.72, .823, .965), (1.0, .858, .925),
        (1.28, .8725, .89), (1.6, .855, .84), (1.85, .80, .77), (2.07, .665, .70)]


def lower_edge(y):
    z = .205
    for center in [1.28, -1.28]:
        d = abs(y - center)
        if d <= .355:
            z = max(z, .31045 + math.sqrt(max(0, .355 ** 2 - d ** 2)))
    return z


def side_point(side, y, t, inset=0):
    bottom = lower_edge(y)
    top = sample(BODY, y, 2)
    z = lerp(bottom, top, t)
    w = sample(BODY, y, 1)
    # Concave door scallop, full rear haunch and rolled sill.
    waist = -.034 * math.sin(PI * t) ** 2 * math.exp(-(y / 1.1) ** 4)
    roll = -.075 * (1 - t) ** 3
    return (side * (w + waist + roll - inset), y, z)


def surface_side(side, ya, yb, parent):
    return grid("Sculpted door skin" if parent != GROUP else "Wing skin", lambda u, v: side_point(side, lerp(ya, yb, u), v), max(8, int((yb - ya) * 85)), 14, M["red"], parent)


def rim_loop(points, material, r=.006, parent=None):
    tube("Perimeter seal", points, r, material, True, parent=parent)


def oval_logo(at, scale=1, facing="front", parent=None):
    # Three overlapping ovals, built as geometry.
    x, y, z = at
    def p(u, v, depth=0):
        if facing == "side":
            return (x + depth, y + u * scale, z + v * scale)
        return (x + u * scale, y + depth, z + v * scale)
    ell("Hybrid emblem backing", (.058 * scale, .008, .04 * scale), at, M["blue"], parent)
    for a, b, cx, cz in [(.055, .036, 0, 0), (.018, .033, 0, 0), (.045, .016, 0, .009)]:
        points = [p(cx + a * math.cos(t * TAU / 40), cz + b * math.sin(t * TAU / 40), -.009 if facing == "rear" else .009) for t in range(40)]
        tube("Toyota oval", points, .0028 * scale, M["chrome"], True, parent=parent)


def textured_quad(name, corners, material, parent=None):
    return mesh(name, corners, [(0, 1, 2, 3)], material, False, parent, [(0, 0), (1, 0), (1, 1), (0, 1)])


def lens_surface(name, boundary, material, bulge=.003, parent=None):
    # Smooth radial patch avoids offset spikes on a non-planar solidified ngon.
    center=sum((Vector(p) for p in boundary),Vector())/len(boundary)
    ring=[]
    count=len(boundary)
    for i in range(count):
        a,b,c,d=[Vector(boundary[j%count]) for j in [i-1,i,i+1,i+2]]
        for k in range(8):
            t=k/8
            ring.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    verts=[tuple(center+Vector((0,bulge,0)))]
    faces=[]
    for r in range(1,7):
        f=r/6
        for p in ring:verts.append(tuple(center.lerp(p,f)+Vector((0,bulge*(1-f*f),0))))
    n=len(ring)
    for i in range(n):faces.append((0,1+i,1+(i+1)%n))
    for r in range(5):
        a=1+r*n;b=a+n
        for i in range(n):faces.append((a+i,b+i,b+(i+1)%n,a+(i+1)%n))
    return mesh(name,verts,faces,material,parent=parent)


def build_body():
    global GROUP
    GROUP = empty("Body", parent=CAR)
    box("Floor pan", (1.43, 2.72, .065), (0, -.12, .205), M["underbody"], .05)
    box("Cabin carpet", (1.38, 1.95, .045), (0, -.15, .265), M["cloth"], .03)
    for side in [-1, 1]:
        surface_side(side, -1.87, -1.23, GROUP)
        surface_side(side, .79, 2.07, GROUP)
        # Four actual separate doors including their glazing and interior cards.
        for front in [True, False]:
            ya, yb = (-.38, .784) if front else (-1.225, -.386)
            hinge = (side * .80, yb, .91)
            door = empty("Door_" + ("F" if front else "R") + ("L" if side < 0 else "R"), hinge, CAR)
            door["hinge_axis"] = "local +Z in Blender; +Y in glTF/Godot"
            door["open_angle_rad"] = side * 1.05
            surface_side(side, ya, yb, door)
            edge = [side_point(side, lerp(ya, yb, i / 60), 0) for i in range(61)]
            edge += [side_point(side, yb, i / 18) for i in range(1, 19)]
            edge += [side_point(side, lerp(yb, ya, i / 60), 1) for i in range(1, 61)]
            edge += [side_point(side, ya, 1 - i / 18) for i in range(1, 18)]
            rim_loop(edge, M["gap"], .0022, door)
            # Window edges derived from side photograph, not opaque cabin blocks.
            yz = [(ya + .025, 1.016), (yb - .07, .990), (.32, 1.389), (ya + .02, 1.434)] if front else [(-1.205, 1.058), (-.411, 1.017), (-.407, 1.435), (-.89, 1.408), (-1.14, 1.279)]
            points = [(side * (.783 - .22 * (z - 1)), y, z) for y, z in yz]
            panel("Clear side glass", points, M["glass"], .003, .005, door)
            rim_loop(points, M["black"], .013, door)
            # Upper painted frames, B pillar satin trim.
            tube("Painted upper door frame", [(p[0] + side * .004, p[1], p[2] + .009) for p in points[1:]], .018, M["red"], False, parent=door)
            box("B pillar applique", (.025, .07, .415), (side * .738, -.398, 1.22), M["black"], .005, parent=door)
            yy = ya + .17
            x = side * (sample(BODY, yy, 1) + .007)
            ell("Handle recess", (.009, .108, .031), (x, yy, .976 if front else 1.022), M["red_dark"], door)
            box("Body colour pull handle", (.032, .151, .023), (x + side * .012, yy, .985 if front else 1.031), M["red"], .011, parent=door)
            if front and side < 0:
                ell("Mechanical lock barrel", (.004, .008, .008), (x + side * .03, yy - .05, .985), M["chrome"], door)
            # Inner door surface has its own thickness; opening reveals no hollow plane.
            z0 = lower_edge((ya + yb) / 2) + .05
            box("Door inner shell", (.038, yb - ya - .03, .48), (side * .709, (ya + yb) / 2, .65), M["trim"], .018, parent=door)
            box("Fabric door insert", (.013, (yb - ya) * .70, .15), (side * .719, (ya + yb) / 2, .83), M["cloth"], .04, parent=door)
            box("Armrest", (.10, (yb - ya) * .67, .065), (side * .692, (ya + yb) / 2, .70), M["trim"], .028, parent=door)
            box("Door pull pocket", (.013, .18, .07), (side * .637, yb - .29, .77), M["black"], .025, parent=door)
            box("Interior release", (.02, .10, .018), (side * .627, yb - .25, .79), M["satin"], .008, parent=door)
            box("Door map pocket", (.075, (yb - ya) * .73, .11), (side * .669, (ya + yb) / 2, .39), M["black"], .025, parent=door)
            for i in range(4 if front and side < 0 else 1):
                box("Electric window switch", (.022, .031, .007), (side * .67, yb - .26 - i * .044, .738), M["black"], .004, parent=door)
            # Two front woofers plus two tweeters = standard four-speaker arrangement.
            if front:
                for r in [.025, .045, .065]:
                    tube("Speaker grille ring", [(side * .716, yb - .16 + r * math.cos(a * TAU / 40), .48 + r * math.sin(a * TAU / 40)) for a in range(40)], .001, M["satin"], True, parent=door)
            for y in [ya + .08, yb - .08]:
                tube("Inner door seal", [(side * .739, y, .3), (side * .739, y, .93)], .008, M["gap"], parent=door)
        # Recessed sill and wheel housings under the doors.
        box("Painted sill", (.11, 1.76, .07), (side * .766, -.15, .215), M["red"], .027)
        box("Scuff plate", (.075, 1.12, .014), (side * .703, .02, .258), M["satin"], .008)
        for yy in [-1.28, 1.28]:
            path = [(side * (.858 if yy > 0 else .862), yy + .358 * math.cos(t * PI / 55), .31045 + .358 * math.sin(t * PI / 55)) for t in range(56)]
            tube("Rolled painted arch lip", path, .013, M["red"])
            verts, faces = [], []
            for j in range(49):
                a = j * PI / 48
                for xx in [.64, .847]:
                    verts.append((side * xx, yy + .348 * math.cos(a), .31045 + .348 * math.sin(a)))
            for j in range(48):
                faces.append((2*j, 2*j+1, 2*j+3, 2*j+2))
            mesh("Wheel well liner", verts, faces, M["underbody"])
        # Rear quarter pillars follow the swelling hip.
        panel("C pillar", [(side*.666,-.90,1.43),(side*.737,-1.12,1.31),(side*.849,-1.48,1.03),(side*.795,-1.65,1.05),(side*.65,-1.26,1.42)],M["red"],.025,.018)
        panel("Quarter window black infill",[(side*.737,-1.12,1.31),(side*.849,-1.48,1.03),(side*.813,-1.21,1.045)],M["gloss"],.01,.006)
        tube("A pillar", [(side*.785,.846,.984),(side*.743,.719,1.10),(side*.68,.49,1.31),(side*.631,.27,1.424)], .033, M["red"])
        tube("Interior A pillar trim", [(side*.749,.818,1.0),(side*.704,.69,1.12),(side*.642,.47,1.32),(side*.6,.26,1.418)], .025, M["headliner"])
        # Body-colour mirrors with integrated direction indicators.
        mirror_parent = bpy.data.objects["Door_F" + ("L" if side < 0 else "R")]
        panel("Mirror triangular mounting", [(side*.785,.79,1.0),(side*.756,.67,1.16),(side*.788,.61,1.0)], M["black"], .015, .008, mirror_parent)
        tube("Mirror stalk", [(side*.79,.71,1.049),(side*.92,.71,1.075)], .025, M["black"], parent=mirror_parent)
        ell("Mirror body colour shell", (.103,.123,.061), (side*.927,.695,1.091), M["red"],mirror_parent)
        ell("Mirror lower black trim", (.102,.121,.022), (side*.927,.686,1.058), M["black"],mirror_parent)
        ell("Mirror reflective lens", (.088,.006,.043), (side*.933,.581,1.09),M["mirror"],mirror_parent)
        tube("Mirror indicator lens", [(side*.988,.76,1.078),(side*1.019,.7,1.08),(side*1.006,.64,1.08)],.005,M["indicator"],parent=mirror_parent)
    # Bonnet: gently domed central sheet with controlled shoulder break.
    def hood(u,v):
        y=lerp(.81,2.035,u); x=lerp(-1,1,v)
        w=sample([(.81,.774),(1.45,.793),(1.588,.790),(1.838,.625),(1.963,.402),(2.035,.39)],y,1)
        z=sample(BODY,y,2)+.038+.026*(1-x*x)
        y-=.045*x*x*u
        return (x*w,y,z)
    hood_obj=grid("Bonnet",hood,38,44,M["red"])
    for side in [-1,1]:
        def shoulder(u,v,s=side):
            y=lerp(.81,1.54,u)
            h=Vector(hood((y-.81)/(2.035-.81),0 if s<0 else 1))
            q=Vector(side_point(s,h.y,1))
            return tuple(h.lerp(q,v))
        grid("Bonnet to wing shoulder",shoulder,38,8,M["red"])
        def lamp_outer_wing(u,v,s=side):
            y=lerp(1.54,2.035,u)
            xx=sample([(1.54,.81),(1.622,.800),(1.946,.581),(1.963,.416),(2.035,.413)],y,1)
            zz=sample([(1.54,.82),(1.622,.805),(1.946,.726),(1.963,.722),(2.035,.715)],y,1)
            a=Vector((s*xx,y,zz));b=Vector(side_point(s,y,1))
            return tuple(a.lerp(b,v))
        grid("Outboard lamp wing return",lamp_outer_wing,32,8,M["red"])
    tube("Bonnet shutline",[hood(1,i/44) for i in range(45)],.002,M["gap"])
    for side in [-1,1]:
        tube("Bonnet shoulder crease",[hood(i/35,.08 if side<0 else .92) for i in range(36)],.002,M["red_dark"])
    # Roof is one thin shell, no sunroof or black bitone paint.
    def roof(u,v):
        y=lerp(-1.18,.29,u); x=lerp(-1,1,v)
        width=.685-.035*(abs(2*u-1)**3)
        z=1.5-.039*x*x-.024*abs(2*u-1)**4
        return (x*width,y,z)
    roof_obj=grid("Stock painted roof",roof,42,32,M["red"])
    sol=roof_obj.modifiers.new("Steel roof", "SOLIDIFY");sol.thickness=.012
    grid("Roof headlining",lambda u,v:(roof(u,v)[0]*.97,roof(u,v)[1],roof(u,v)[2]-.026),24,20,M["headliner"])
    for side in [-1,1]:
        tube("Roof gutter",[roof(i/42,0 if side<0 else 1) for i in range(43)],.006,M["black"])
        tube("Painted roof side rail",[(side*.677,-1.10,1.447),(side*.688,-.75,1.459),(side*.689,-.30,1.459),(side*.678,.17,1.441),(side*.643,.285,1.435)],.022,M["red"])
    # Clear laminated windshield, with rubber frit border.
    def wind(u,v):
        x=lerp(-1,1,v);w=lerp(.752,.635,u)
        return (x*w,lerp(.853,.28,u)-.025*(1-x*x),lerp(.98,1.426,u)+.018*(1-x*x))
    grid("Windscreen",wind,22,32,M["glass"])
    perimeter=[wind(0,i/32) for i in range(33)]+[wind(i/22,1) for i in range(1,23)]+[wind(1,1-i/32) for i in range(1,33)]+[wind(1-i/22,0) for i in range(1,22)]
    rim_loop(perimeter,M["black"],.014)
    box("Scuttle",(1.42,.14,.035),(0,.878,.947),M["black"],.018)
    for side in [-1,1]:
        tube("Front wiper arm",[(side*.37,.85,.978),(side*.23,.82,.999),(side*.07,.79,1.018)],.005,M["black"])
        tube("Wiper rubber",[(side*.58,.804,.997),(side*.08,.779,1.022)],.006,M["black"])
    box("Roof lamp console",(.19,.16,.027),(0,.13,1.425),M["headliner"],.02)
    box("Dome light lens",(.11,.065,.008),(0,.13,1.408),M["lens"],.01)
    for side in [-1,1]:
        box("Sun visor",(.30,.15,.018),(side*.32,.35,1.399),M["headliner"],.014)
        tube("Rear grab handle",[(side*.648,-.63,1.355),(side*.614,-.63,1.38),(side*.614,-.81,1.38),(side*.648,-.81,1.355)],.009,M["headliner"])
    rod("Interior mirror stem",(0,.55,1.34),(0,.58,1.393),.01,M["black"])
    box("Manual interior mirror",(.22,.038,.065),(0,.55,1.318),M["black"],.018)
    box("Interior mirror silver",(.197,.003,.047),(0,.528,1.319),M["mirror"],.013)
    # Body-colour fuel door on left rear wing.
    rim_loop([(-.873,-1.31+.085*math.cos(a*TAU/48),.866+.079*math.sin(a*TAU/48)) for a in range(48)],M["gap"],.002)
    # Factory roof aerial, separate from the fictional mast.
    fin=ell("Shark fin aerial",(.035,.092,.028),(0,-.95,1.491),M["red"])
    fin.rotation_euler.x=.17


def build_front():
    # Curved bumper fascia with a real grille opening.
    outer=[(-.665,.70),(-.80,.71),(-.846,.59),(-.847,.37),(-.79,.19),(-.52,.18),(.52,.18),(.79,.19),(.847,.37),(.846,.59),(.80,.71),(.665,.70)]
    inner=[(-.26,.67),(-.48,.65),(-.57,.56),(-.62,.42),(-.45,.235),(-.28,.216),(.28,.216),(.45,.235),(.62,.42),(.57,.56),(.48,.65),(.26,.67)]
    verts=[]
    for ring in [outer,inner]:
        for x,z in ring:verts.append((x,2.07-.17*(abs(x)/.85)**2,z))
    faces=[(i,(i+1)%12,(i+1)%12+12,i+12) for i in range(12)]
    o=mesh("Front bumper sculpt",verts,faces,M["red"])
    sub=o.modifiers.new("Fascia curvature","SUBSURF");sub.levels=2
    sol=o.modifiers.new("Bumper return","SOLIDIFY");sol.thickness=.025
    grid("Upper nose bridge",lambda u,v:(lerp(-.53,.53,v),2.066-.17*(abs(lerp(-.53,.53,v))/.85)**2,lerp(.675,.752,u)+.01*(1-(2*v-1)**2)),6,36,M["red"])
    outline=[(x,2.073-.17*(abs(x)/.85)**2,z) for x,z in inner]
    panel("Recessed grille backing",[(x,y-.035,z) for x,y,z in outline],M["black"],.01,.014)
    tube("Grille surround",outline,.012,M["black"],True)
    # Horizontal tiered grille, no GR G-pattern.
    for z,w in [(.25,.43),(.29,.49),(.33,.53),(.37,.565),(.42,.59),(.47,.574),(.52,.535),(.57,.502),(.62,.462),(.65,.40)]:
        tube("Horizontal grille blade",[(lerp(-w,w,i/24),2.063-.17*(abs(lerp(-w,w,i/24))/.85)**2,z) for i in range(25)],.0065,M["grille"])
    for x in [-.40,-.25,-.1,.1,.25,.40]:
        tube("Grille vertical support",[(x,2.034-.13*x*x,.30),(x,2.034-.13*x*x,.65)],.004,M["black"])
    box("Front plate plinth",(.55,.028,.135),(0,2.081,.438),M["black"],.009)
    textured_quad("Front display plate",[(.26,2.097,.388),(-.26,2.097,.388),(-.26,2.097,.498),(.26,2.097,.498)],M["plate"])
    oval_logo((0,2.075,.746),1.18)
    for side in [-1,1]:
        # The eyebrow is swept back strongly on the outboard corner.
        points=[(side*.405,1.963,.727),(side*.57,1.946,.731),(side*.785,1.622,.809),(side*.79,1.588,.872),(side*.63,1.838,.828)]
        lens_surface("LED headlamp black housing",points,M["black"])
        center=Vector((side*.635,1.842,.786))
        inner=[tuple(center+(Vector(p)-center)*.89+Vector((0,.009,0))) for p in points]
        lens_surface("Headlamp reflector",inner,M["chrome"])
        lens=[tuple(Vector(p)+Vector((0,.017,0))) for p in points]
        lens_surface("Headlamp clear cover",lens,M["lampglass"])
        tube("LED daytime guide",[(side*.447,1.979,.742),(side*.57,1.963,.749),(side*.758,1.699,.816),(side*.771,1.638,.857)],.006,M["drl"])
        for i in range(3):
            x=side*(.56+i*.052); y=1.933-i*.073;z=.763+i*.016
            ell("LED projector optic",(.025,.012,.024),(x,y,z),M["lens"])
            box("Projector reflector separator",(.006,.028,.04),(x+side*.029,y,z),M["chrome"],.002)
        tube("Lamp upper seal",[(side*.63,1.838,.835),(side*.79,1.588,.88)],.004,M["gap"])
        # Vertical black foglight housing at the outer corner.
        panel("Fog lamp intake",[(side*.694,1.969,.284),(side*.798,1.921,.299),(side*.793,1.915,.552),(side*.763,1.93,.588)],M["black"],.01,.02)
        rod("Fog chrome surround",(side*.747,1.931,.326),(side*.747,1.953,.326),.033,M["chrome"])
        rod("LED fog lamp",(side*.747,1.949,.326),(side*.747,1.96,.326),.025,M["lens"])
    tube("Front lower black lip",[(-.75,1.96,.191),(-.47,2.068,.178),(0,2.075,.175),(.47,2.068,.178),(.75,1.96,.191)],.012,M["black"])


def build_rear():
    global GROUP
    old=GROUP
    hatch=empty("Hatch",(0,-1.16,1.439),CAR)
    hatch["open_angle_rad"]=-1.05
    # Swept rear screen and gloss black light bridge are characteristic of XP210.
    def backglass(u,v):
        x=lerp(-1,1,v)
        return (x*lerp(.587,.698,u),lerp(-1.19,-1.723,u)-.025*(1-x*x),lerp(1.427,1.062,u)+.014*(1-x*x))
    grid("Heated rear glass",backglass,20,30,M["glass"],hatch)
    edge=[backglass(0,i/30) for i in range(31)]+[backglass(i/20,1) for i in range(1,21)]+[backglass(1,1-i/30) for i in range(1,31)]+[backglass(1-i/20,0) for i in range(1,20)]
    rim_loop(edge,M["black"],.018,hatch)
    for i in range(1,10):
        tube("Heater trace",[tuple(Vector(backglass(i/11,t/28))+Vector((0,-.002,0))) for t in range(29)],.0007,M["heater"],parent=hatch,sides=4)
    grid("Tailgate lower skin",lambda u,v:(lerp(-.73,.73,v)*(1-.06*u),lerp(-1.75,-1.857,u)-.025*(1-(2*v-1)**2),lerp(1.076,.543,u)),24,30,M["red"],hatch)
    box("Gloss black tail lamp bridge",(1.50,.065,.16),(0,-1.78,1.015),M["gloss"],.06,parent=hatch)
    oval_logo((0,-1.831,1.015),1.12,"rear",hatch)
    tube("Rear wiper",[(.14,-1.759,1.10),(.0,-1.765,1.13),(-.32,-1.731,1.16)],.006,M["black"],parent=hatch)
    box("Spoiler upper lip",(1.29,.175,.045),(0,-1.24,1.446),M["red"],.026,parent=hatch)
    box("High mounted brake lamp",(.32,.018,.014),(0,-1.331,1.443),M["brake"],.006,parent=hatch)
    box("Tailgate latch",(.15,.024,.021),(0,-1.865,.84),M["black"],.008,parent=hatch)
    rod("Reverse camera lens",(.10,-1.866,.832),(.10,-1.877,.832),.009,M["lens"],parent=hatch)
    for side in [-1,1]:
        yz=[(side*.43,-1.812,1.074),(side*.74,-1.748,1.093),(side*.821,-1.642,1.072),(side*.804,-1.683,.92),(side*.686,-1.795,.892),(side*.452,-1.832,.954)]
        panel("Rear lamp housing",yz,M["black"],.018,.02,hatch)
        tube("Red LED light guide",[(side*.47,-1.835,1.054),(side*.711,-1.789,1.071),(side*.782,-1.698,1.056),(side*.767,-1.731,.951),(side*.685,-1.817,.927),(side*.48,-1.852,.974)],.011,M["brake"],parent=hatch)
        panel("Reversing indicator lens",[(side*.504,-1.852,1.013),(side*.687,-1.81,1.028),(side*.712,-1.80,.979),(side*.528,-1.85,.99)],M["lens"],.005,.006,hatch)
    # Structural boot below movable hatch; no collision geometry in the GLB.
    GROUP=old
    box("Rear bumper",(1.55,.245,.33),(0,-1.715,.386),M["red"],.09)
    box("Rear lower valance",(1.20,.085,.155),(0,-1.843,.285),M["black"],.055)
    box("Rear plate recess",(.57,.045,.14),(0,-1.863,.62),M["black"],.014,parent=hatch)
    textured_quad("Rear display plate",[(-.26,-1.89,.569),(.26,-1.89,.569),(.26,-1.89,.679),(-.26,-1.89,.679)],M["plate"],hatch)
    for side in [-1,1]:
        box("Rear reflector",(.14,.012,.028),(side*.665,-1.835,.345),M["brake"],.012)
        box("Boot inner quarter trim",(.16,.63,.32),(side*.57,-1.24,.47),M["trim"],.04)
    box("Load floor",(1.0,.68,.035),(0,-1.39,.381),M["cloth"],.02)
    box("Parcel shelf",(1.05,.49,.023),(0,-1.20,.981),M["cloth"],.02)


def lathe_x(name, x, y, z, profile, material, parent, segments=80):
    verts,faces,uv=[],[],[]
    for i in range(segments):
        a=TAU*i/segments
        for j,(axial,r) in enumerate(profile):
            verts.append((x+axial,y+r*math.cos(a),z+r*math.sin(a)))
            uv.append((i/segments,j/(len(profile)-1)))
    n=len(profile)
    for i in range(segments):
        for j in range(n-1):
            k=i*n+j;q=((i+1)%segments)*n+j
            faces.append((k,q,q+1,k+1))
    return mesh(name,verts,faces,material,parent=parent,uv=uv)


def build_wheels():
    for axle,y,track in [("F",1.28,1.518),("R",-1.28,1.514)]:
        for side in [-1,1]:
            x=side*track/2;z=.31045
            steer=empty("Steer_"+axle+("L" if side<0 else "R"),(x,y,z),CAR)
            wheel=empty("Wheel_"+axle+("L" if side<0 else "R"),(0,0,0),steer)
            wheel["spin_axis"]="local +X; rolling forward decreases angle"
            wheel["radius_m"]=.31045
            wheel["tyre"]="195/55 R16"
            profile=[(-.073,.200),(-.088,.217),(-.0975,.255),(-.096,.280),(-.084,.302),(-.07,.31045),(.07,.31045),(.084,.302),(.096,.28),(.0975,.255),(.088,.217),(.073,.2)]
            lathe_x("195-55 R16 tyre",x,y,z,profile,M["rubber"],wheel,96)
            # Four circumferential tread channels, actual geometry.
            for dx in [-.057,-.020,.020,.057]:
                lathe_x("Tread channel",x,y,z,[(dx-.002,.3105),(dx+.002,.3105)],M["groove"],wheel,96)
            for i in range(56):
                a=TAU*i/56
                for sign in [-1,1]:
                    pts=[]
                    for j in range(3):
                        dx=sign*(.029+j*.028);aa=a+j*.018*sign
                        pts.append((x+dx,y+.3103*math.cos(aa),z+.3103*math.sin(aa)))
                    tube("Tread lateral sipe",pts,.0015,M["groove"],parent=wheel,sides=4)
            face=x+side*.092
            lathe_x("Alloy barrel",x,y,z,[(-.078,.18),(-.078,.200),(.08,.200),(.095,.19),(.095,.179)],M["alloy_dark"],wheel)
            for rr in [.201,.204,.23,.282]:
                tube("Rim lip" if rr<.21 else "Sidewall rib",[(face,y+rr*math.cos(a*TAU/80),z+rr*math.sin(a*TAU/80)) for a in range(80)],.0025 if rr<.21 else .0008,M["chrome"] if rr<.21 else M["rubber"],True,parent=wheel)
            rod("Ventilated brake disc",(x+side*.055,y,z),(x+side*.064,y,z),.132,M["disc"],wheel,64)
            rod("Disc hub",(x+side*.064,y,z),(x+side*.07,y,z),.065,M["alloy_dark"],wheel)
            box("Standard brake caliper",(.04,.055,.13),(x+side*.064,y-.105,z),M["disc"],.014,parent=wheel)
            # Machined face 16-inch pattern: eight angular split spokes.
            for i in range(8):
                a=TAU*i/8
                def p(r,t,offset=0):return (face+side*offset,y+r*math.cos(a+t),z+r*math.sin(a+t))
                verts=[p(.055,-.15),p(.115,-.09),p(.195,-.23),p(.199,-.12),p(.135,.07),p(.198,.23),p(.198,.31),p(.109,.12),p(.055,.15)]
                panel("Split-spoke black casting",verts,M["alloy_dark"],.019,.004,wheel)
                for branch in [-1,1]:
                    panel("Diamond cut spoke face",[p(.065,branch*.07,.006),p(.123,branch*.055,.006),p(.195,branch*.205,.006),p(.197,branch*.26,.006),p(.113,branch*.12,.006)],M["alloy"],.003,.001,wheel)
            rod("Wheel centre cap",(face,y,z),(face+side*.012,y,z),.043,M["alloy_dark"],wheel)
            # Side-facing brand emblem without adding text to tyre sidewalls.
            for ra,rb in [(.028,.020),(.009,.019),(.024,.009)]:
                tube("Wheel oval mark",[(face+side*.014,y+ra*math.cos(a*TAU/30),z+rb*math.sin(a*TAU/30)) for a in range(30)],.0018,M["chrome"],True,parent=wheel)
            for i in range(5):
                a=TAU*i/5;yy=y+.058*math.cos(a);zz=z+.058*math.sin(a)
                rod("Wheel nut",(face,yy,zz),(face+side*.008,yy,zz),.008,M["chrome"],wheel,6)


def build_interior():
    global GROUP
    GROUP=empty("Interior",parent=CAR)
    # Dashboard wraps around the binnacle, with passenger shelf and soft upper pad.
    box("Dashboard upper soft touch",(1.39,.36,.125),(0,.595,.914),M["soft"],.055)
    box("Dashboard lower fascia",(1.32,.22,.16),(0,.495,.792),M["trim"],.05)
    box("Passenger glovebox",(.50,.14,.17),(.389,.423,.694),M["trim"],.025)
    tube("Glovebox shutline",[(.15,.347,.757),(.62,.347,.757),(.63,.347,.63),(.15,.347,.63)],.0015,M["gap"])
    box("Glovebox release",(.085,.012,.015),(.385,.343,.734),M["black"],.005)
    tube("Satin dashboard highlight",[(.10,.393,.827),(.42,.393,.831),(.65,.416,.86)],.003,M["satin"])
    for side in [-1,1]:
        box("Outer air vent frame",(.155,.062,.095),(side*.622,.437,.895),M["satin"],.039)
        box("Outer vent opening",(.137,.068,.076),(side*.622,.43,.895),M["black"],.032)
        for i in range(4):
            box("Air vent louvre",(.114,.012,.003),(side*.622,.391,.873+i*.014),M["trim"],.001)
        box("Vent direction tab",(.019,.014,.008),(side*.622,.382,.895),M["satin"],.002)
        ell("Door tweeter grille",(.023,.033,.015),(side*.678,.667,.984),M["black"])
    # Binocular cluster, three explicit readings in original screen artwork.
    box("Instrument binnacle hood",(.485,.19,.13),(-.371,.526,1.005),M["soft"],.055)
    textured_quad("Binocular instrument display",[(-.588,.421,.965),(-.154,.421,.965),(-.154,.421,1.065),(-.588,.421,1.065)],M["cluster"])
    for xx in [-.512,-.23]:
        tube("Binocular hood rim",[(xx+.091*math.cos(a*TAU/50),.418,1.016+.059*math.sin(a*TAU/50)) for a in range(50)],.008,M["black"],True)
    # Standard Toyota Touch 3 seven-inch unit: screen diagonal is .1778m.
    box("Touch 3 tablet bezel",(.218,.048,.144),(0,.462,1.02),M["gloss"],.013)
    sw=.15497;sh=.08717
    textured_quad("7 inch touchscreen",[(-sw/2,.436,.991-sh/2+.025),(sw/2,.436,.991-sh/2+.025),(sw/2,.436,.991+sh/2+.025),(-sw/2,.436,.991+sh/2+.025)],M["touch"])
    for side in [-1,1]:
        for i in range(4):
            box("Touch physical shortcut",(.015,.005,.005),(side*.096,.434,1.06-i*.022),M["satin"],.001)
        rod("Touch rotary dial",(side*.09,.435,.963),(side*.09,.425,.963),.009,M["satin"])
    box("Centre vent surround",(.252,.063,.052),(0,.437,.91),M["gloss"],.018)
    for side in [-1,1]:
        box("Centre vent opening",(.093,.012,.025),(side*.064,.399,.908),M["black"],.005)
        for i in range(3):
            box("Centre vent slat",(.086,.008,.002),(side*.064,.39,.9+i*.008),M["trim"],.001)
    panel("Hazard triangle",[(-.008,.385,.931),(.008,.385,.931),(0,.385,.945)],M["brake"],.001,.001)
    # Single-zone automatic HVAC: no second temperature display.
    box("Automatic climate panel",(.242,.06,.067),(0,.373,.797),M["gloss"],.022)
    textured_quad("Single zone HVAC display",[(-.067,.341,.783),(.067,.341,.783),(.067,.341,.815),(-.067,.341,.815)],M["climate"])
    for side in [-1,1]:
        rod("HVAC dial chrome",(side*.095,.34,.798),(side*.095,.325,.798),.023,M["satin"])
        rod("HVAC dial rubber",(side*.095,.324,.798),(side*.095,.319,.798),.019,M["black"])
    box("USB 12V panel",(.19,.045,.04),(0,.366,.715),M["black"],.007)
    box("USB socket",(.014,.004,.006),(-.044,.341,.715),M["satin"],.001)
    rod("12V cap",(.055,.343,.716),(.055,.337,.716),.014,M["black"])
    # Leather shifter and EPB; no manual handbrake, no third pedal.
    box("Centre console",(.224,.79,.17),(0,-.075,.42),M["trim"],.035)
    box("Piano black shift surround",(.198,.29,.024),(0,.176,.518),M["gloss"],.035)
    box("Leather gaiter",(.09,.125,.06),(.015,.18,.553),M["leather"],.023)
    rod("Gear stalk",(.015,.18,.55),(.015,.18,.668),.011,M["satin"])
    ell("Leather e-CVT selector",(.024,.033,.045),(.015,.18,.672),M["leather"])
    tube("Selector gate surround",[(-.058,.28,.537),(-.058,.08,.537),(.065,.08,.537),(.065,.28,.537)],.003,M["satin"],True)
    for i in range(4):
        box("PRDB gate index",(.008,.009,.001),(-.079,.25-i*.038,.533),M["letter"] , .001)
    for j in range(2):
        tube("Cupholder lip",[(.065*math.cos(i*TAU/44),-.115-j*.15+.065*math.sin(i*TAU/44),.488) for i in range(44)],.008,M["black"],True)
        rod("Cupholder well",(0,-.115-j*.15,.455),(0,-.115-j*.15,.483),.058,M["black"])
    box("Electric parking brake switch",(.043,.055,.018),(-.065,-.035,.516),M["black"],.008)
    box("Hold switch",(.035,.028,.008),(-.065,-.084,.51),M["black"],.005)
    box("Front storage armrest",(.165,.25,.09),(0,-.465,.579),M["cloth"],.027)
    # Three spoke, leather multifunction wheel with tilted axis and working pivot.
    steer=empty("SteeringWheel",(-.37,.256,.932),CAR)
    steer["steering_ratio_reference"]=13.6
    center=Vector((-.37,.256,.932))
    axis=Vector((0,.945,-.327)); up=Vector((0,.327,.945));right=Vector((1,0,0))
    def p(x,z,depth=0):return tuple(center+right*x+up*z+axis*depth)
    tube("Leather steering rim",[p(.174*math.cos(a*TAU/88),.174*math.sin(a*TAU/88)) for a in range(88)],.015,M["leather"],True,parent=steer,sides=10)
    rod("Steering column",(-.37,.30,.909),(-.37,.491,.843),.039,M["black"])
    for s in [-1,1]:
        panel("Steering spoke",[p(s*.045,.03),p(s*.151,.035),p(s*.153,-.035),p(s*.057,-.025)],M["black"],.027,.012,steer)
        panel("Spoke button surround",[p(s*.07,.02,-.017),p(s*.135,.024,-.017),p(s*.14,-.018,-.017),p(s*.075,-.018,-.017)],M["satin"],.003,.006,steer)
        for k in range(3):
            ell("Steering multifunction key",(.008,.004,.006),p(s*(.086+k*.018),.008,-.024),M["black"],steer)
        tube("Stalk",[p(s*.07,-.018,.10),p(s*.223,.01,.10)],.009,M["black"],parent=GROUP)
    panel("Lower spoke",[p(-.041,-.045),p(.041,-.045),p(.038,-.15),p(-.038,-.15)],M["satin"],.022,.012,steer)
    ell("Airbag wheel centre",(.069,.031,.062),tuple(center-axis*.01),M["leather"],steer)
    for ra,rb in [(.027,.018),(.009,.018),(.024,.009)]:
        tube("Steering oval badge",[p(ra*math.cos(a*TAU/40),rb*math.sin(a*TAU/40),-.043) for a in range(40)],.0017,M["chrome"],True,parent=steer)
    # Standard Trend ignition cylinder; Comfort Pack push start is absent.
    rod("Mechanical ignition barrel",(-.229,.389,.842),(-.225,.376,.842),.016,M["satin"])
    for x,y,w,h in [(-.405,.651,.085,.095),(-.267,.67,.045,.115)]:
        box("Brake pedal" if w>.05 else "Accelerator pedal",(w,.025,h),(x,y,.391),M["rubber"],.009,rotation=(-.32,0,0))
        rod("Pedal lever",(x,y+.02,.39),(x,y+.09,.53),.008,M["disc"])
        for i in range(5):
            box("Pedal grip rib",(w*.85,.005,.003),(x,y-.014,.36+i*.015),M["trim"],.001)
    box("Driver heel mat",(.43,.39,.009),(-.37,.415,.292),M["rubber"],.023)
    box("Passenger heel mat",(.43,.39,.009),(.37,.415,.292),M["rubber"],.023)
    # Standard fabric front seats with separate bolsters, inserts and headrests.
    for side in [-1,1]:
        x=side*.365
        for xx in [x-.17,x+.17]:
            box("Seat runner",(.026,.49,.035),(xx,-.16,.307),M["disc"],.005)
        box("Seat cushion",(.458,.475,.112),(x,-.124,.448),M["cloth"],.055)
        box("Seat cushion centre insert",(.284,.365,.023),(x,-.092,.511),M["cloth"],.035)
        for s in [-1,1]:
            o=ell("Fabric cushion bolster",(.070,.22,.066),(x+s*.183,-.12,.502),M["cloth"])
            o.rotation_euler.y=s*.10
        back=box("Seat backrest",(.415,.115,.50),(x,-.407,.796),M["cloth"],.058,rotation=(-.12,0,0))
        box("Backrest inset",(.271,.024,.345),(x,-.335,.79),M["cloth"],.045,rotation=(-.12,0,0))
        for s in [-1,1]:
            b=ell("Seat back bolster",(.063,.079,.203),(x+s*.17,-.349,.8),M["cloth"])
            b.rotation_euler.x=-.12
            tube("Upholstery seam",[(x+s*.134,-.313,.622),(x+s*.138,-.312,.86),(x+s*.099,-.337,.963)],.0012,M["seam"])
        for dx in [-.064,.064]:
            rod("Headrest steel post",(x+dx,-.421,1.0),(x+dx,-.425,1.126),.006,M["chrome"])
        box("Front adjustable headrest",(.219,.111,.195),(x,-.433,1.16),M["cloth"],.04,rotation=(-.08,0,0))
        box("Seatbelt buckle",(.029,.04,.071),(x-side*.227,-.261,.478),M["black"],.009)
        box("Buckle red release",(.025,.026,.008),(x-side*.227,-.254,.515),M["brake"],.004)
        tube("Front seat belt webbing",[(side*.68,-.42,1.23),(side*.67,-.46,.78),(side*.65,-.42,.43)],.010,M["belt"],sides=4)
        box("Belt upper guide",(.035,.055,.07),(side*.684,-.40,1.23),M["black"],.012)
        if side<0:
            tube("Manual height adjust lever",[(x-.23,-.3,.42),(x-.23,-.18,.42)],.012,M["black"])
    # Rear bench split 60/40, three belts, three headrests, standard black cloth.
    box("Rear bench cushion",(1.20,.43,.105),(0,-.905,.49),M["cloth"],.055)
    for xa,xb in [(-.60,.12),(.127,.60)]:
        box("60-40 folding rear seatback",(xb-xa,.12,.43),((xa+xb)/2,-1.136,.77),M["cloth"],.045,rotation=(-.10,0,0))
    for x in [-.414,0,.414]:
        for dx in [-.045,.045]:
            rod("Rear headrest post",(x+dx,-1.158,.95),(x+dx,-1.16,1.065),.005,M["chrome"])
        box("Rear headrest",(.191,.095,.125),(x,-1.17,1.09),M["cloth"],.032)
        box("Rear belt buckle",(.027,.034,.035),(x+.11,-.99,.555),M["black"],.007)
        box("Rear buckle release",(.021,.027,.006),(x+.11,-.989,.575),M["brake"],.003)
    for side in [-1,1]:
        tube("Rear belt",[(side*.623,-1.2,1.17),(side*.58,-1.18,.68),(side*.54,-.96,.55)],.01,M["belt"],sides=4)
        for dx in [-.1,.1]:
            tube("ISOFIX anchor",[(side*.395+dx,-1.02,.55),(side*.395+dx,-1.0,.553)],.003,M["satin"])
    GROUP=empty("Sockets",parent=CAR)
    for name,p in {"DriverHips":(-.365,-.14,.525),"PassengerHips":(.365,-.14,.525),"DriverEye":(-.365,-.24,1.17),"SteeringGripL":(-.537,.256,.932),"SteeringGripR":(-.203,.256,.932),"BrakePad":(-.405,.637,.391),"AcceleratorPad":(-.267,.656,.391),"DoorExitL":(-1.12,-.05,.27),"MastRoof":(0,-.10,1.50)}.items():
        empty(name,p,GROUP)


def apply_and_merge():
    # Preserve every articulation pivot; merge static pieces by material per pivot.
    bpy.ops.object.select_all(action="DESELECT")
    for o in list(bpy.context.scene.objects):
        if o.type=="MESH" and o.parent:
            bpy.context.view_layer.objects.active=o
            for m in list(o.modifiers):
                bpy.ops.object.modifier_apply(modifier=m.name)
            if not o.data.uv_layers:
                o.data.uv_layers.new(name="UVMap")
    buckets={}
    for o in list(bpy.context.scene.objects):
        if o.type=="MESH" and o.parent:
            key=(o.parent.name,o.data.materials[0].name)
            buckets.setdefault(key,[]).append(o)
    for (parent,material),objects in buckets.items():
        bpy.ops.object.select_all(action="DESELECT")
        for o in objects:o.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        if len(objects)>1:bpy.ops.object.join()
        o=bpy.context.object;o.name=parent+"__"+material
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bpy.ops.object.select_all(action="DESELECT")


def create_animation():
    scene=bpy.context.scene
    scene.render.fps=30
    # One inspection clip, with the initial frame stock and shut.
    for name in ["Door_FL","Door_FR","Door_RL","Door_RR"]:
        o=bpy.data.objects[name]
        for f,value in [(1,0),(30,o["open_angle_rad"]),(70,o["open_angle_rad"]),(100,0)]:
            o.rotation_euler.z=value;o.keyframe_insert("rotation_euler",frame=f,group="Doors")
        o.animation_data.action.name=name+"_OpenClose"
    o=bpy.data.objects["Hatch"]
    for f,value in [(1,0),(30,-1.05),(70,-1.05),(100,0)]:
        o.rotation_euler.x=value;o.keyframe_insert("rotation_euler",frame=f)
    o.animation_data.action.name="Hatch_OpenClose"
    scene.frame_set(1)


def select_car():
    bpy.ops.object.select_all(action="DESELECT")
    CAR.select_set(True)
    for o in CAR.children_recursive:o.select_set(True)
    bpy.context.view_layer.objects.active=CAR


def export_glb(path):
    select_car()
    bpy.ops.export_scene.gltf(filepath=str(path),export_format="GLB",use_selection=True,
        export_apply=True,export_yup=True,export_extras=True,export_animations=True,
        export_animation_mode="ACTIONS",export_frame_range=False,export_cameras=False,
        export_lights=False,export_materials="EXPORT")


def render_views():
    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    scene.cycles.samples=40
    scene.cycles.use_denoising=True
    scene.view_settings.look="AgX - Medium High Contrast"
    scene.view_settings.exposure=-.4
    scene.render.resolution_x=1440
    scene.render.resolution_y=1000
    scene.render.resolution_percentage=100
    scene.world.color=(.32,.32,.32)
    # Large softboxes give readable reflections without downloaded HDRIs.
    def area(name,p,power,size,target):
        d=bpy.data.lights.new(name,"AREA");d.energy=power;d.shape="DISK";d.size=size
        o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=p
        o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()
    area("Key",(1,3,6),1500,5,(0,0,.7))
    area("Long sidebox",(-4,-1,3),1100,4,(0,0,.7))
    area("Rim softbox",(3,-4,4),1800,3,(0,0,1))
    ground=box("Studio floor",(200,200,.05),(0,0,-.04),mat("Studio grey",(.14,.16,.18),.65),0,parent=None)
    ground.parent=None
    d=bpy.data.cameras.new("Inspection camera");camera=bpy.data.objects.new("Inspection camera",d);scene.collection.objects.link(camera);scene.camera=camera
    def shot(name,p,target,lens=52):
        camera.location=p;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat("-Z","Y").to_euler();d.lens=lens
        scene.render.filepath=str(REPORT/(name+".png"));bpy.ops.render.render(write_still=True)
    shot("front_three_quarter",(-4.5,6.0,2.8),(0,.10,.76))
    shot("rear_three_quarter",(4.5,-5.8,2.8),(0,0,.8))
    shot("side",(-6.8,.1,1.10),(0,.10,.76),54)
    # Open the physical front doors for an unobstructed cockpit photograph.
    scene.frame_set(45)
    shot("cockpit",(-.0,-.59,1.20),(0,.66,.82),17)
    shot("open_doors",(-4.7,4.7,2.8),(0,0,.80))
    scene.frame_set(1)
    bpy.data.objects.remove(ground,do_unlink=True)


def main():
    global CAR,M
    parser=argparse.ArgumentParser()
    parser.add_argument("--render",action="store_true")
    parser.add_argument("--overwrite",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    OUT.mkdir(parents=True,exist_ok=True);REPORT.mkdir(parents=True,exist_ok=True)
    SOURCE.mkdir(parents=True,exist_ok=True)
    if (OUT/"yaris_trend_2022.glb").exists() and not args.overwrite:
        raise FileExistsError("Use --overwrite to replace generated vehicle")
    bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
    CAR=empty("YarisTrend2022")
    CAR["units"]="metres";CAR["asset_status"]="PHOTO_RECONSTRUCTION_REQUIRES_ART_REVIEW"
    CAR["model_year"]=2022;CAR["grade"]="Italian Hybrid Trend, standard equipment"
    CAR["paint_reference"]="Emotional Red 3U5; uncalibrated display approximation"
    CAR["body_length_m"]=3.94;CAR["body_width_m"]=1.745;CAR["body_height_m"]=1.5
    CAR["wheelbase_m"]=2.56
    M={
        "red":mat("Emotional_Red_3U5",(.38,.004,.011),.24,.18,.8),
        "red_dark":mat("Red_recess",(.24,.006,.012),.30,.25,.5),
        "black":mat("Satin_black",(.008,.009,.011),.42),
        "gap":mat("Panel_gaps",(.003,.003,.004),.9),
        "underbody":mat("Underbody",(.012,.014,.016),.88),
        "gloss":mat("Piano_black",(.008,.009,.012),.2,.08,.45),
        "grille":mat("Grille_blades",(.025,.028,.031),.38,.20),
        "rubber":mat("Tyre_rubber",(.018,.021,.024),.82),
        "groove":mat("Tread_recess",(.004,.005,.006),.93),
        "alloy":mat("Machined_alloy",(.59,.64,.68),.24,.88),
        "alloy_dark":mat("Gloss_black_alloy",(.019,.021,.024),.24,.72),
        "disc":mat("Brake_and_structural_metal",(.21,.23,.24),.49,.78),
        "chrome":mat("Bright_chrome",(.74,.78,.81),.16,.94),
        "satin":mat("Satin_silver",(.26,.29,.32),.42,.65),
        "blue":mat("Hybrid_badge_blue",(.015,.12,.32),.2,.65,.7),
        "glass":mat("Clear_standard_glass",(.48,.61,.66),.10,.08,.7,alpha=.15),
        "lampglass":mat("Clear_lamp_cover",(.79,.84,.88),.08,.08,.8,alpha=.11),
        "mirror":mat("Mirror_silver",(.67,.73,.78),.07,1),
        "brake":mat("Red_light_guides",(.54,.008,.013),.22,.16,.6,emission=.25),
        "drl":mat("White_LED_guides",(.78,.89,1),.2,.1,.2,emission=.8),
        "indicator":mat("Clear_indicator",(.55,.59,.60),.16,.25,.5),
        "lens":mat("Lamp_optics",(.47,.54,.59),.16,.55,.5),
        "heater":mat("Heater_traces",(.16,.10,.065),.7,.3),
        "trim":mat("Cabin_moulded_trim",(.032,.035,.039),.69),
        "soft":mat("Soft_touch_dashboard",(.022,.025,.028),.78),
        "cloth":texmat("Standard_black_fabric","cloth.png",.94),
        "leather":mat("Black_leather_controls",(.018,.020,.023),.57),
        "headliner":mat("Charcoal_headlining",(.12,.125,.13),.97),
        "seam":mat("Grey_stitching",(.12,.13,.14),.9),
        "belt":mat("Seatbelt_webbing",(.016,.018,.02),.95),
        "letter":mat("Control_markings",(.57,.61,.66),.6),
        "touch":texmat("Touch3_7inch","touch_7.png",.28,True),
        "cluster":texmat("MY22_binocular_display","cluster.png",.28,True),
        "climate":texmat("Single_zone_auto_HVAC","climate.png",.28,True),
        "plate":texmat("Non_registered_display_plate","plate.png",.38),
    }
    build_body();build_front();build_rear();build_wheels();build_interior()
    bpy.context.scene.unit_settings.system="METRIC"
    bpy.context.scene.unit_settings.scale_length=1
    # Save an editable source before any game-oriented joining.
    create_animation()
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/"yaris_trend_2022.blend"),compress=True)
    apply_and_merge()
    export_glb(OUT/"yaris_trend_2022.glb")
    dg=bpy.context.evaluated_depsgraph_get()
    triangles=0;meshes=0
    for o in CAR.children_recursive:
        if o.type=="MESH":
            m=o.evaluated_get(dg).to_mesh();m.calc_loop_triangles();triangles+=len(m.loop_triangles);meshes+=1;o.evaluated_get(dg).to_mesh_clear()
    stats={"blender":bpy.app.version_string,"triangles_lod0":triangles,"mesh_primitives":meshes,"units":"m","status":"photo_reconstruction_art_review_pending"}
    # Optional independent lower detail exports, preserve articulation names.
    for lod,ratio in [(1,.45),(2,.18)]:
        for o in CAR.children_recursive:
            if o.type=="MESH" and len(o.data.polygons)>150:
                m=o.modifiers.new("LOD reduction","DECIMATE");m.ratio=ratio
        export_glb(OUT/f"yaris_trend_2022_lod{lod}.glb")
        for o in CAR.children_recursive:
            if o.type=="MESH":
                for m in list(o.modifiers):
                    if m.type=="DECIMATE":o.modifiers.remove(m)
    (REPORT/"mesh_stats.json").write_text(json.dumps(stats,indent=2)+"\n",encoding="utf8")
    if args.render:render_views()
    print("YARIS_EXPORT_COMPLETE",json.dumps(stats))


if __name__=="__main__":
    main()
