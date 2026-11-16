import array
import bpy
import math
import os
from mathutils import Vector, Matrix, Quaternion

# ============================================================
# FORD OFFICE RECEPTION - BLOCKOUT v1
# Blender 4.x / 5.x
# Units: metres
# This is an approximate reconstruction from one photograph.
# All geometry is editable and organized into collections.
# ============================================================

# ---------- Clean scene ----------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.collections,):
    for block in list(datablocks):
        if block.name != "Collection":
            try:
                datablocks.remove(block)
            except:
                pass

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
engine_ids = {
    item.identifier
    for item in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items
}
if 'BLENDER_EEVEE_NEXT' in engine_ids:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
elif 'BLENDER_EEVEE' in engine_ids:
    scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1440
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100

# ---------- Collections ----------
def make_collection(name):
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    return col

COL_ARCH = make_collection("01_ARCHITECTURE")
COL_RECEPTION = make_collection("02_RECEPTION")
COL_FURNITURE = make_collection("03_FURNITURE")
COL_DECOR = make_collection("04_DECORATION")
COL_LIGHTS = make_collection("05_LIGHTS_AND_CAMERA")

ACTIVE_COLLECTION = COL_ARCH

def move_to_collection(obj, collection=None):
    collection = collection or ACTIVE_COLLECTION
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
    return obj

# ---------- Materials ----------
def material(name, color, roughness=0.6, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat

MAT_FLOOR = material("Porcelain - warm white", (0.78, 0.76, 0.72), 0.22)
MAT_WALL = material("Warm white wall", (0.84, 0.82, 0.78), 0.82)
MAT_CEILING = material("Ceiling white", (0.91, 0.89, 0.85), 0.9)
MAT_WOOD = material("Oak - feature wall", (0.48, 0.27, 0.12), 0.48)
MAT_WOOD_LIGHT = material("Oak - slats", (0.64, 0.40, 0.22), 0.45)
MAT_BLUE = material("Deep blue accent wall", (0.015, 0.075, 0.18), 0.8)
MAT_COUNTER = material("Reception counter - ivory", (0.88, 0.85, 0.80), 0.32)
MAT_DARK = material("Dark metal", (0.035, 0.04, 0.045), 0.32, 0.65)
MAT_SCREEN = material("TV screen", (0.008, 0.018, 0.045), 0.16, 0.12)
MAT_SOFA = material("Sofa - deep blue fabric", (0.025, 0.12, 0.32), 0.92)
MAT_CREAM = material("Chair - warm cream fabric", (0.82, 0.77, 0.68), 0.9)
MAT_PEACH = material("Accent pouf - muted peach", (0.67, 0.32, 0.24), 0.9)
MAT_RUG = material("Rug - blue", (0.025, 0.12, 0.30), 1.0)
MAT_LEAF = material("Plant leaves", (0.045, 0.22, 0.075), 0.8)
MAT_POT = material("Planter - stone", (0.48, 0.45, 0.39), 0.8)
MAT_WHITE = material("Light diffuser", (1.0, 0.96, 0.84), 0.35)

# ---------- Geometry helpers ----------
def cube(name, location, dimensions, mat=None, bevel=0.0, collection=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    if bevel > 0:
        mod = obj.modifiers.new("Soft edges", 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        obj.modifiers.new("Weighted corner normals", 'WEIGHTED_NORMAL')
    return move_to_collection(obj, collection)

def cylinder(name, location, radius, depth, mat=None, vertices=48, collection=None, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    if mat:
        obj.data.materials.append(mat)
    if bevel > 0:
        mod = obj.modifiers.new("Rounded edges", 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        obj.modifiers.new("Weighted normals", 'WEIGHTED_NORMAL')
    return move_to_collection(obj, collection)

def uv_sphere(name, location, scale, mat=None, collection=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    return move_to_collection(obj, collection)

def add_text(name, body, location, size, mat, rotation=(math.pi/2, 0, 0), collection=None):
    data = bpy.data.curves.new(name, type='FONT')
    data.body = body
    data.size = size
    data.extrude = 0.006
    data.align_x = 'CENTER'
    data.align_y = 'CENTER'
    obj = bpy.data.objects.new(name, data)
    (collection or ACTIVE_COLLECTION).objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    if mat:
        obj.data.materials.append(mat)
    return obj

# ---------- Room shell ----------
ACTIVE_COLLECTION = COL_ARCH
ROOM_W = 12.0
ROOM_D = 10.0
WALL_H = 3.5
# Open front (y=-5) for easy viewing and navigation.
cube("Floor slab", (0, 0, -0.12), (ROOM_W, ROOM_D, 0.24), MAT_FLOOR, 0.04)
cube("Back wall", (0, 4.92, WALL_H/2), (ROOM_W, 0.16, WALL_H), MAT_WALL)
cube("Left wall - blue lounge", (-5.92, 0.0, WALL_H/2), (0.16, ROOM_D, WALL_H), MAT_BLUE)
cube("Right wall", (5.92, 0.0, WALL_H/2), (0.16, ROOM_D, WALL_H), MAT_WALL)
cube("Ceiling", (0, 0, WALL_H + 0.12), (ROOM_W, ROOM_D, 0.24), MAT_CEILING)

# ---------- Feature wall and wooden slats ----------
ACTIVE_COLLECTION = COL_RECEPTION
cube("Oak feature wall panel", (-1.55, 4.79, 1.78), (7.0, 0.12, 3.05), MAT_WOOD, 0.015)
# Narrow vertical slats across the visible feature wall.
for i in range(43):
    x = -4.95 + i * 0.16
    cube(f"Oak vertical slat {i+1:02d}", (x, 4.70, 1.78), (0.035, 0.055, 3.02),
         MAT_WOOD_LIGHT, 0.008)
# Lower horizontal seam / panel detail
cube("Feature wall lower trim", (-1.55, 4.66, 0.48), (7.0, 0.035, 0.035), MAT_WOOD, 0.005)

# Ford wordmark placeholder: editable text, not an exact trademark logo.
logo_mat = material("Logo pale silver", (0.78, 0.84, 0.92), 0.25, 0.35)
add_text("FORD logo placeholder", "Ford", (-1.55, 4.60, 2.35), 0.78, logo_mat)

# Reception desk: main body + raised stepped return.
cube("Reception desk main body", (0.05, 2.75, 0.55), (3.65, 1.05, 1.10), MAT_COUNTER, 0.12)
cube("Reception desk upper top", (0.05, 2.70, 1.14), (3.78, 1.10, 0.12), MAT_COUNTER, 0.06)
cube("Reception desk raised right section", (1.55, 2.70, 1.30), (0.75, 1.08, 0.36), MAT_COUNTER, 0.07)
cube("Reception desk side return", (1.82, 2.25, 0.70), (0.20, 0.18, 1.15), MAT_COUNTER, 0.04)

# ---------- TV wall ----------
ACTIVE_COLLECTION = COL_ARCH
cube("TV wall mounting panel", (5.78, 2.55, 2.18), (0.08, 3.0, 2.1), MAT_WALL, 0.02)
cube("Television body", (5.63, 2.65, 2.30), (0.12, 2.45, 1.42), MAT_DARK, 0.045)
cube("Television screen", (5.555, 2.65, 2.30), (0.025, 2.34, 1.31), MAT_SCREEN, 0.012)

# ---------- Lounge rug ----------
ACTIVE_COLLECTION = COL_FURNITURE
cube("Blue patterned rug base", (-2.35, -1.45, 0.015), (5.0, 3.55, 0.035), MAT_RUG, 0.025)
# Simple cream geometric rug motif placeholders.
for row in range(5):
    for col in range(8):
        x = -4.35 + col * 0.57
        y = -2.75 + row * 0.62
        motif = cube(f"Rug motif {row+1}-{col+1}", (x, y, 0.039), (0.22, 0.16, 0.012),
                     MAT_CREAM, 0.015)
        motif.rotation_euler[2] = math.radians(25 if (row+col) % 2 else -25)

# Sofa along left foreground: long seat, back and end arms.
cube("Blue sofa seat", (-4.15, -1.25, 0.55), (1.25, 4.0, 0.62), MAT_SOFA, 0.22)
cube("Blue sofa back", (-4.72, -1.15, 1.05), (0.35, 4.0, 1.20), MAT_SOFA, 0.18)
cube("Blue sofa front arm", (-4.15, -3.20, 0.85), (1.25, 0.35, 1.05), MAT_SOFA, 0.18)

# Coffee table, low round top and cylindrical base.
cylinder("Coffee table base", (-2.25, -1.55, 0.24), 0.58, 0.42, MAT_WOOD, bevel=0.05)
cylinder("Coffee table top", (-2.25, -1.55, 0.49), 0.88, 0.12, MAT_COUNTER, bevel=0.045)

# Small side table.
cylinder("Side table top", (-1.15, -0.15, 0.56), 0.43, 0.09, MAT_WOOD_LIGHT, bevel=0.025)
cylinder("Side table pedestal", (-1.15, -0.15, 0.28), 0.12, 0.48, MAT_DARK)

# Chair helper: stylized upholstered lounge chair with four splayed legs.
def lounge_chair(name, x, y, zrot=0, seat_mat=MAT_CREAM):
    # Local components are created then rotated around chair centre.
    parts = []
    parts.append(cube(name + " seat", (x, y, 0.63), (0.92, 0.86, 0.30), seat_mat, 0.22))
    parts.append(cube(name + " back", (x, y+0.30, 1.12), (0.94, 0.28, 0.92), seat_mat, 0.22))
    # legs, approximate splay
    for sx in (-1, 1):
        for sy in (-1, 1):
            leg = cube(name + " leg", (x+sx*0.32, y+sy*0.29, 0.31), (0.055, 0.055, 0.58), MAT_DARK, 0.015)
            leg.rotation_euler[1] = sx * math.radians(10)
            parts.append(leg)
    # Rotate complete chair around its centre in XY.
    if zrot:
        pivot = Vector((x, y, 0))
        for obj in parts:
            p = Vector(obj.location) - pivot
            p = Matrix.Rotation(zrot, 3, 'Z') @ p
            obj.location = pivot + p
            obj.rotation_euler[2] += zrot
    return parts

lounge_chair("Lounge chair A", -1.35, 0.25, math.radians(-12), MAT_CREAM)
lounge_chair("Lounge chair B", 0.55, -2.85, math.radians(160), MAT_CREAM)

# Accent pouf.
cylinder("Peach round pouf", (-0.35, -2.15, 0.38), 0.58, 0.72, MAT_PEACH, bevel=0.12)

# ---------- Plants ----------
ACTIVE_COLLECTION = COL_DECOR
def make_plant(name, x, y, height=1.5):
    cylinder(name + " planter", (x, y, 0.36), 0.28, 0.68, MAT_POT, bevel=0.035)
    # stem
    cylinder(name + " stem", (x, y, 0.95 + height*0.20), 0.025, height*0.55, MAT_LEAF)
    for i in range(9):
        angle = i * (2*math.pi/9)
        r = 0.24 + 0.08*(i%2)
        z = 1.05 + (i%4)*0.16
        leaf = uv_sphere(name + f" leaf {i+1}", (x+math.cos(angle)*r, y+math.sin(angle)*r, z),
                         (0.12, 0.075, 0.32), MAT_LEAF)
        leaf.rotation_euler[1] = math.cos(angle)*0.45
        leaf.rotation_euler[0] = math.sin(angle)*0.45
    uv_sphere(name + " crown", (x, y, 1.55), (0.32, 0.30, 0.38), MAT_LEAF)

make_plant("Reception plant left", -4.95, 3.7, 1.7)
make_plant("Reception plant right", 2.9, 3.75, 1.7)
make_plant("Lounge plant", -5.35, -3.7, 1.5)

# Small plant on reception counter.
cylinder("Counter plant pot", (1.35, 2.85, 1.30), 0.13, 0.22, MAT_POT)
for i in range(5):
    a = i*2*math.pi/5
    uv_sphere("Counter plant leaf", (1.35+math.cos(a)*0.13, 2.85+math.sin(a)*0.13, 1.52),
              (0.08, 0.055, 0.16), MAT_LEAF)

# ---------- Secondary lounge hints ----------
ACTIVE_COLLECTION = COL_DECOR
# Frames on the blue wall (wall is x=-5.92, facing into room)
for i, (y, z, w, h) in enumerate([(-0.8, 2.25, 0.72, 0.62), (0.35, 2.25, 0.78, 0.62)]):
    cube(f"Wall frame {i+1}", (-5.78, y, z), (0.055, w, h), MAT_DARK, 0.025)
    cube(f"Wall art print {i+1}", (-5.742, y, z), (0.018, w*0.88, h*0.86), MAT_COUNTER, 0.008)

# ---------- Ceiling lighting placeholders ----------
ACTIVE_COLLECTION = COL_LIGHTS
# Recessed light panels.
for x in (-4.2, -1.4, 1.4, 4.2):
    for y in (-3.5, 0.0, 3.2):
        cube(f"Ceiling light panel {x}-{y}", (x, y, 3.47), (0.48, 0.32, 0.025), MAT_WHITE, 0.035)

# Pendant rings were thin toruses that read as stray circles and curved lines.
# Ceiling panels above are the practical lights.

# ---------- Lighting ----------
def area_light(name, location, target, power, size, color=(1.0, 0.88, 0.72)):
    data = bpy.data.lights.new(name, type='AREA')
    data.energy = power
    data.shape = 'DISK'
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    COL_LIGHTS.objects.link(obj)
    obj.location = location
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return obj

for light_obj in (
    area_light("Key softbox", (0, -2.5, 3.25), (0, 1.5, 0.8), 1700, 7.0),
    area_light("Reception wash", (-1.8, 3.0, 3.25), (-1.5, 4.5, 1.5), 900, 3.5),
    area_light("Lounge fill", (-4.0, -2.5, 3.1), (-2.5, -1.0, 0.7), 700, 3.0),
    area_light("Right wall fill", (4.8, -0.5, 3.0), (3.5, 2.0, 1.2), 600, 3.0),
):
    # Keep the light in the render. Hide the viewport gizmo so the big
    # circles and direction lines are not drawn through the room.
    light_obj.hide_set(True)

# ---------- Camera ----------
bpy.ops.object.camera_add(location=(2.8, -4.55, 2.45))
camera = bpy.context.object
camera.name = "Camera - reference view"
target = Vector((0.0, 2.1, 1.45))
direction = target - camera.location
camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
camera.data.lens = 30
camera.data.clip_end = 200
scene.camera = camera
move_to_collection(camera, COL_LIGHTS)

# ---------- World and render ----------
world = bpy.data.worlds.new("Office ambient world") if not bpy.data.worlds else bpy.data.worlds[0]
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.48, 0.58, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35

scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
# Use AgX when available (Blender 4.x+), otherwise fall back to Filmic.
view_transforms = {
    item.identifier
    for item in bpy.types.ColorManagedViewSettings.bl_rna.properties['view_transform'].enum_items
}
scene.view_settings.view_transform = 'AgX' if 'AgX' in view_transforms else 'Filmic'

# ---------- Srini avatar ----------
# Mixamo idle stays on the NLA track. "Wave Hi" is our own bone animation
# (right shoulder, arm, forearm, hand) combined on top of that idle.
COL_AVATAR = make_collection("06_AVATAR")

def find_glb(filename):
    candidates = []
    script_path = globals().get("__file__")
    if script_path:
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(script_path)), "avatar", filename))
    if bpy.data.filepath:
        candidates.append(os.path.join(os.path.dirname(bpy.data.filepath), "avatar", filename))
    candidates.append(os.path.join(r"c:\Users\sethu\Downloads\office-setup\avatar", filename))
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    raise FileNotFoundError(f"Could not find avatar/{filename} next to this script.")

def world_bounds(obj):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    points = [evaluated.matrix_world @ vertex.co for vertex in evaluated.data.vertices]
    xs = [point.x for point in points]
    ys = [point.y for point in points]
    zs = [point.z for point in points]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)

def local_delta(swings):
    rotation = Quaternion((1.0, 0.0, 0.0, 0.0))
    axes = {'X': (1.0, 0.0, 0.0), 'Y': (0.0, 1.0, 0.0), 'Z': (0.0, 0.0, 1.0)}
    for axis, degrees in swings:
        rotation = rotation @ Quaternion(axes[axis], math.radians(degrees))
    return rotation

def wave_params(frame, start=1):
    """Raise amount (0-1) and wrist/forearm swing in degrees.

    The wave occupies 168 frames beginning at `start`: idle, raise, two
    waves, then the arm comes back down.
    """
    local = frame - (start - 1)
    if local <= 28 or local >= 168:
        return 0.0, 0.0, 0.0
    if local < 52:
        t = (local - 28) / (52 - 28)
        smooth = t * t * (3.0 - 2.0 * t)
        return smooth, 0.0, 0.0
    if local < 132:
        t = (local - 52) / (132 - 52)
        swing = math.sin(t * math.pi * 4.0)
        return 1.0, swing * 36.0, swing * 14.0
    t = (local - 132) / (168 - 132)
    smooth = 1.0 - (t * t * (3.0 - 2.0 * t))
    return smooth, 0.0, 0.0

TOTAL_FRAMES = 336
SRINI_WAVE_START = 1
KARTHI_WAVE_START = 169
# Srini keeps his spot. Karthi stands just in front of lounge chair B.
SRINI_XY = (1.7, -1.2)
KARTHI_XY = (0.35, -2.05)

def import_avatar(filename, name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=find_glb(filename))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    arm = next(obj for obj in imported if obj.type == 'ARMATURE')
    mesh = next(obj for obj in imported if obj.type == 'MESH' and obj.parent == arm)
    for obj in imported:
        if obj not in (arm, mesh):
            bpy.data.objects.remove(obj, do_unlink=True)
    arm.name = name
    mesh.name = f"{name} body"
    move_to_collection(arm, COL_AVATAR)
    move_to_collection(mesh, COL_AVATAR)
    return arm, mesh

def stand_on_floor(arm, mesh, xy, height=1.75):
    # Uniform scale keeps the glTF Y-up rotation. Do not assign rotation_euler.
    _minx, _maxx, _miny, _maxy, min_z, max_z = world_bounds(mesh)
    imported_height = max(max_z - min_z, 0.01)
    arm.scale = arm.scale * (height / imported_height)
    arm.location.x = xy[0]
    arm.location.y = xy[1]
    arm.location.z = 0.0
    bpy.context.view_layer.update()
    _minx, _maxx, _miny, _maxy, min_z, _maxz = world_bounds(mesh)
    arm.location.z -= min_z - 0.005

def face_toward(arm, target_xy):
    """Yaw around world Z so the character's forward (-Y) points at target_xy."""
    bpy.context.view_layer.update()
    origin = arm.matrix_world.translation.copy()
    direction_x = target_xy[0] - origin.x
    direction_y = target_xy[1] - origin.y
    if direction_x * direction_x + direction_y * direction_y < 1e-8:
        return
    yaw = math.atan2(direction_x, -direction_y)
    current = arm.matrix_world.copy()
    arm.matrix_world = (
        Matrix.Translation(origin)
        @ Matrix.Rotation(yaw, 4, 'Z')
        @ Matrix.Translation(-origin)
        @ current
    )

def show_texture_in_solid(mesh):
    if not mesh.material_slots:
        return None
    avatar_mat = mesh.material_slots[0].material
    base_image = None
    if avatar_mat and avatar_mat.node_tree:
        for link in avatar_mat.node_tree.links:
            if link.to_node.type == 'BSDF_PRINCIPLED' and link.to_socket.name == 'Base Color':
                if link.from_node.type == 'TEX_IMAGE' and link.from_node.image:
                    base_image = link.from_node.image
                    avatar_mat.node_tree.nodes.active = link.from_node
    if base_image and base_image.size[0] > 0:
        width, height = base_image.size
        pixel_buffer = array.array('f', [0.0]) * (width * height * 4)
        base_image.pixels.foreach_get(pixel_buffer)
        step = 16
        red = green = blue = 0.0
        count = 0
        for y in range(0, height, step):
            row = y * width
            for x in range(0, width, step):
                index = (row + x) * 4
                if pixel_buffer[index + 3] < 0.5:
                    continue
                red += pixel_buffer[index]
                green += pixel_buffer[index + 1]
                blue += pixel_buffer[index + 2]
                count += 1
        if count:
            avatar_mat.diffuse_color = (red / count, green / count, blue / count, 1.0)
    mesh.color = (1.0, 1.0, 1.0, 1.0)
    return avatar_mat

def shorten_and_hide_bones(arm):
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for edit_bone in arm.data.edit_bones:
        direction = edit_bone.tail - edit_bone.head
        if direction.length < 1e-8:
            continue
        child_lengths = [(child.head - edit_bone.head).length for child in edit_bone.children]
        child_lengths = [length for length in child_lengths if length > 1.0]
        length = min(child_lengths) if child_lengths else 8.0
        edit_bone.tail = edit_bone.head + direction.normalized() * length
    bpy.ops.object.mode_set(mode='OBJECT')
    arm.data.display_type = 'OCTAHEDRAL'
    for bone in arm.data.bones:
        bone.hide = True

def bake_wave(arm, action_name, wave_start, total_frames, raised):
    anim_data = arm.animation_data
    idle_action = anim_data.action
    for track in anim_data.nla_tracks:
        track.mute = True
        track.name = f"{arm.name} Mixamo Idle (source)"
    anim_data.action_blend_type = 'REPLACE'
    if idle_action is not None and getattr(idle_action, "slots", None):
        anim_data.action_slot = idle_action.slots[0]

    bone_names = [pose_bone.name for pose_bone in arm.pose.bones]
    idle_cache = []
    for frame in range(1, 48):
        scene.frame_set(frame)
        idle_cache.append({
            pose_bone.name: (
                tuple(pose_bone.location),
                Quaternion(pose_bone.rotation_quaternion),
                tuple(pose_bone.scale),
            )
            for pose_bone in arm.pose.bones
        })

    posed_frames = []
    for frame in range(1, total_frames + 1):
        source = idle_cache[(frame - 1) % len(idle_cache)]
        raise_amount, hand_swing, forearm_swing = wave_params(frame, wave_start)
        posed = {}
        for name in bone_names:
            location, rotation, scale = source[name]
            rotation = Quaternion(rotation)
            if raise_amount > 0.0 and name in raised:
                swings = [(axis, degrees * raise_amount) for axis, degrees in raised[name]]
                if name.endswith("RightHand"):
                    swings.append(("Z", hand_swing))
                elif name.endswith("RightForeArm"):
                    swings.append(("Z", forearm_swing))
                rotation = rotation @ local_delta(swings)
            posed[name] = (location, rotation, scale)
        posed_frames.append(posed)

    existing = bpy.data.actions.get(action_name)
    if existing is not None:
        bpy.data.actions.remove(existing)
    action = bpy.data.actions.new(action_name)
    action.use_fake_user = True
    slot = action.slots.new('OBJECT', arm.name)
    layer = action.layers.new("Pose")
    strip = layer.strips.new(type='KEYFRAME')
    channelbag = strip.channelbag(slot, ensure=True)

    def write_curve(data_path, index, values):
        curve = channelbag.fcurves.new(data_path, index=index)
        points = curve.keyframe_points
        points.add(len(values))
        for index_frame, value in enumerate(values):
            points[index_frame].co = (index_frame + 1, value)
            points[index_frame].interpolation = 'LINEAR'
        curve.update()

    for name in bone_names:
        path = f'pose.bones["{name}"]'
        for index in range(3):
            write_curve(path + ".location", index, [posed_frames[frame][name][0][index] for frame in range(total_frames)])
        for index in range(4):
            write_curve(path + ".rotation_quaternion", index, [posed_frames[frame][name][1][index] for frame in range(total_frames)])
        for index in range(3):
            write_curve(path + ".scale", index, [posed_frames[frame][name][2][index] for frame in range(total_frames)])

    anim_data.action = action
    anim_data.action_slot = slot
    anim_data.action_blend_type = 'REPLACE'
    anim_data.action_influence = 1.0
    action.use_cyclic = True
    return action

srini_arm, srini_mesh = import_avatar("srini.glb", "srini")
karthi_arm, karthi_mesh = import_avatar("karthi.glb", "karthi")
stand_on_floor(srini_arm, srini_mesh, SRINI_XY)
stand_on_floor(karthi_arm, karthi_mesh, KARTHI_XY)
face_toward(srini_arm, KARTHI_XY)
face_toward(karthi_arm, SRINI_XY)
srini_mat = show_texture_in_solid(srini_mesh)
karthi_mat = show_texture_in_solid(karthi_mesh)
shorten_and_hide_bones(srini_arm)
shorten_and_hide_bones(karthi_arm)
# Same gesture, different bind axes. Srini's palm needs a half turn.
# Karthi's palm already faces forward, and his raise is the mirrored swing.
srini_raised = {
    "mixamorig:RightShoulder": [("Z", 22)],
    "mixamorig:RightArm": [("X", -78), ("Z", 50)],
    "mixamorig:RightForeArm": [("X", -56)],
    "mixamorig:RightHand": [("X", 8), ("Y", 180)],
}
karthi_raised = {
    "mixamorig:RightShoulder": [("Z", -30)],
    "mixamorig:RightArm": [("X", -70), ("Z", -60)],
    "mixamorig:RightForeArm": [("X", -40)],
    "mixamorig:RightHand": [("X", 8)],
}
srini_wave = bake_wave(srini_arm, "Srini Wave Hi", SRINI_WAVE_START, TOTAL_FRAMES, srini_raised)
karthi_wave = bake_wave(karthi_arm, "Karthi Wave Hi", KARTHI_WAVE_START, TOTAL_FRAMES, karthi_raised)

scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = TOTAL_FRAMES
scene.frame_current = 1

scene["Project"] = "Ford office reception - approximate single-photo reconstruction"
scene["Room dimensions"] = "12m wide x 10m deep x 3.5m high (provisional)"
scene["Avatar"] = (
    "Srini stays at his spot and faces Karthi. Karthi stands by lounge chair B facing Srini. "
    "Srini waves on frames 1-168. Karthi waves on frames 169-336."
)
scene["Next step"] = "Press Space. Srini waves first, then Karthi waves back."

for obj in bpy.context.selected_objects:
    obj.select_set(False)
srini_arm.select_set(True)
bpy.context.view_layer.objects.active = srini_arm

for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type != 'VIEW_3D':
            continue
        space = area.spaces.active
        space.region_3d.view_perspective = 'CAMERA'
        shading = space.shading
        shading.type = 'SOLID'
        color_types = {item.identifier for item in shading.bl_rna.properties['color_type'].enum_items}
        if 'TEXTURE' in color_types:
            shading.color_type = 'TEXTURE'
        space.overlay.show_overlays = True
        space.overlay.show_relationship_lines = False
        if hasattr(space.overlay, "show_lights"):
            space.overlay.show_lights = False
        if hasattr(space.overlay, "show_bones"):
            space.overlay.show_bones = False

print("Ford office reception blockout created.")
print("Collections: 01_ARCHITECTURE, 02_RECEPTION, 03_FURNITURE, 04_DECORATION, 05_LIGHTS_AND_CAMERA, 06_AVATAR")
for label, arm, mesh in (("Srini", srini_arm, srini_mesh), ("Karthi", karthi_arm, karthi_mesh)):
    _minx, _maxx, _miny, _maxy, foot_z, head_z = world_bounds(mesh)
    print(f"{label} height {head_z - foot_z:.2f}m, feet at z={foot_z:.3f}, location {tuple(round(v, 3) for v in arm.location)}")
print(f"Actions: {srini_wave.name}, {karthi_wave.name}. Frames 1-{TOTAL_FRAMES}.")
print(f"Solid diffuse Srini {tuple(round(c, 3) for c in srini_mat.diffuse_color)}")
print(f"Solid diffuse Karthi {tuple(round(c, 3) for c in karthi_mat.diffuse_color)}")
