"""Bake actual Godot deformation samples for inspection and render an animation.

Run after build_characters.py and godot/tests/record_occupant_motion.gd.
The generated take is a review of measured physics, not the runtime controller.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
C = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))


def rod(name, a, b, radius, mat, parent):
    direction = Vector(b) - Vector(a)
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=radius, depth=direction.length)
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = (Vector(a) + Vector(b)) * .5
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = direction.to_track_quat('Z', 'Y')
    obj.data.materials.append(mat)
    return obj


def cube(name, at, size, mat, parent):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.name, obj.parent, obj.location, obj.scale = name, parent, at, size
    obj.data.materials.append(mat)
    bevel = obj.modifiers.new('Soft edges', 'BEVEL')
    bevel.width, bevel.segments = .01, 3
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--frame', type=int)
    parser.add_argument('--output', type=Path, default=ROOT/'art/source/generated/animation')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    args.output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art/source/generated/characters/characters.blend'))
    trace = json.loads((ROOT/'art/source/generated/characters/physics_trace.json').read_text())
    scene = bpy.context.scene
    scene.render.fps = trace['fps']
    scene.frame_start, scene.frame_end = 1, len(trace['samples'])
    characters = {key: bpy.data.objects[key] for key in ('Bernie', 'Bianca')}
    characters['Bernie'].location.x = -.40
    characters['Bianca'].location.x = .40
    for key, actor in characters.items():
        arm = bpy.data.objects[key+'_Rig']
        arm.animation_data_create()
        arm.animation_data.action = bpy.data.actions.new(key+'_PhysicalDrivingTake')
        rest = {bone.name: bone.matrix_local.copy() for bone in arm.data.bones}
        actor.rotation_mode = 'QUATERNION'
        for frame, sample in enumerate(trace['samples'], 1):
            source = sample['driver' if key == 'Bernie' else 'lookout']
            scene.frame_set(frame)
            desired = {name: C.inverted() @ Matrix(matrix) @ C @ rest[name]
                       for name, matrix in source['bones'].items()}
            for bone in arm.pose.bones:
                if bone.parent:
                    bone.matrix_basis = (rest[bone.name].inverted() @ rest[bone.parent.name]
                        @ desired[bone.parent.name].inverted() @ desired[bone.name])
                else:
                    bone.matrix_basis = rest[bone.name].inverted() @ desired[bone.name]
            bpy.context.view_layer.update()
            for bone in arm.pose.bones:
                bone.rotation_mode = 'QUATERNION'
                bone.keyframe_insert('location', frame=frame, group=bone.name)
                bone.keyframe_insert('rotation_quaternion', frame=frame, group=bone.name)
            vehicle = C.inverted() @ Matrix(sample['vehicle_transform']) @ C
            actor.rotation_quaternion = vehicle.to_quaternion()
            actor.keyframe_insert('rotation_quaternion', frame=frame)
    # Render the exact post-collision mantle from the engine, not just its bone weights.
    original = bpy.data.objects['Bianca_purple_cape']
    original.hide_render = True
    original.hide_set(True)
    indices = trace['cape_indices']
    triangles = [indices[i:i+3] for i in range(0, len(indices), 3)]
    convert = lambda p: (p[0], -p[2], p[1])
    mesh = bpy.data.meshes.new('CapePhysicsCache')
    mesh.from_pydata([convert(v) for v in trace['samples'][0]['lookout']['cape_vertices']], [], triangles)
    cache = bpy.data.objects.new('Bianca_CapePhysicsCache', mesh)
    scene.collection.objects.link(cache)
    cache.parent = characters['Bianca']
    cache.data.materials.append(original.data.materials[0])
    for face in mesh.polygons:
        face.use_smooth = True
    cache.shape_key_add(name='Basis')
    for frame, sample in enumerate(trace['samples'], 1):
        key = cache.shape_key_add(name=f'Physics_{frame:03d}')
        for vert, point in zip(key.data, sample['lookout']['cape_vertices']):
            vert.co = convert(point)
        for at, value in ((frame-1, 0), (frame, 1), (frame+1, 0)):
            key.value = value
            key.keyframe_insert('value', frame=at)
    dark = bpy.data.materials['Bernie_eyes']
    wood = bpy.data.materials['Bernie_cap']
    cube('Seat cushion', (0, -.04, .135), (.29, .25, .04), dark, characters['Bernie'])
    cube('Seat back', (0, -.13, .27), (.29, .04, .28), dark, characters['Bernie'])
    for side in (-1, 1):
        pedal = bpy.data.objects.new('Pedal pivot', None)
        scene.collection.objects.link(pedal)
        pedal.parent = characters['Bernie']
        pedal.location = (side*.082, .15, .023)
        cube('Pedal pad', (0, .05, -.0105), (.065, .10, .025), dark, pedal)
        for frame, sample in enumerate(trace['samples'], 1):
            press = sample['pedals'][1 if side == -1 else 0]
            pedal.rotation_euler.x = -.12*press
            pedal.keyframe_insert('rotation_euler', frame=frame)
        rod('Coffa appiglio', (side*.18, .31, .454), (side*.18, .14, .480), .009, wood, characters['Bianca'])
        rod('Coffa montante', (side*.30, .31, .01), (side*.30, .31, .454), .012, wood, characters['Bianca'])
    rod('Coffa presa', (-.18, .14, .480), (.18, .14, .480), .009, wood, characters['Bianca'])
    rod('Coffa parapetto', (-.30, .31, .454), (.30, .31, .454), .018, wood, characters['Bianca'])
    mount = bpy.data.objects.new('Steering mount', None)
    scene.collection.objects.link(mount)
    mount.parent = characters['Bernie']
    mount.location, mount.rotation_euler.x = (0, .13, .385), math.radians(90)
    bpy.ops.mesh.primitive_torus_add(major_radius=.075, minor_radius=.008,
                                    major_segments=48, minor_segments=12)
    wheel = bpy.context.object
    wheel.name, wheel.parent, wheel.location = 'Steering wheel', mount, (0, 0, 0)
    wheel.data.materials.append(dark)
    for spoke in range(3):
        angle = spoke*math.tau/3
        rod('Wheel spoke', (0,0,0), (.067*math.cos(angle), .067*math.sin(angle), 0), .004, dark, wheel)
    for frame, sample in enumerate(trace['samples'], 1):
        wheel.rotation_euler.z = -sample['steering']*.30
        wheel.keyframe_insert('rotation_euler', frame=frame)
    camera = scene.camera
    camera.location = (1.20, 3.2, 1.30)
    camera.rotation_euler = (Vector((0, 0, .36))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale = 1.82
    scene.render.resolution_x, scene.render.resolution_y = 960, 640
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 8
    scene.cycles.use_denoising = True
    scene.frame_set(45)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output/'occupant_animation.blend'), compress=True)
    if args.frame:
        scene.frame_set(args.frame)
        scene.render.filepath = str(args.output/f'frame_{args.frame:03d}.png')
        bpy.ops.render.render(write_still=True)
    elif args.render:
        for frame in range(scene.frame_start, scene.frame_end+1):
            scene.frame_set(frame)
            scene.render.filepath = str(args.output/f'frame_{frame:03d}.png')
            bpy.ops.render.render(write_still=True)
    print('BAKED_PHYSICS_TAKE', len(trace['samples']), 'frames')


if __name__ == '__main__':
    main()
