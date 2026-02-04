import os
import math
from mathutils import Vector, Matrix

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def get_or_create_collection(name: str):
    import bpy
    collection = bpy.data.collections.get(name)
    if collection is None :
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection

def look_at_matrix(cam_pos: Vector, target: Vector, up: Vector) -> Matrix:
    forward = (target - cam_pos).normalized()
    right = forward.cross(up)
    if right.length < 1e-8:
        right = forward.orthogonal()
    right.normalize()
    true_up = right.cross(forward).normalized()

    rot = Matrix(
        (
            (right.x, true_up.x, (-forward).x, 0.0),
            (right.y, true_up.y, (-forward).y, 0.0),
            (right.z, true_up.z, (-forward).z, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
    )
    trans = Matrix.Translation(cam_pos)
    return trans @ rot

def set_render_settings(
    scene,
    engine: str,
    res_x: int,
    res_y: int,
    png_compression: int,
    film_transparent: bool,
    cycles_samples: int,
    cycles_denoise: bool,
):
    scene.render.engine = engine
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100

    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.compression = png_compression
    scene.render.film_transparent = bool(film_transparent)

    if engine == "CYCLES":
        scene.cycles.samples = cycles_samples
        scene.cycles.use_denoising = bool(cycles_denoise)

def spherical_points_by_spacing(max_dist: float, sphere_radius: float):
    R = max(1e-6, float(sphere_radius))
    s = max(1e-6, float(max_dist))

    dphi = s / R
    dphi = max(1e-4, min(dphi, math.pi / 4.0))

    pts = []
    pts.append((Vector((0.0, 0.0, -R)), "BOTTOM"))
    pts.append((Vector((0.0, 0.0, R)), "TOP"))

    phi = -math.pi / 2.0 + dphi
    while phi < (math.pi / 2.0 - dphi * 0.5):
        z = R * math.sin(phi)
        r_xy = max(0.0, R * math.cos(phi))

        if r_xy < 1e-9:
            phi += dphi
            continue

        circumference = 2.0 * math.pi * r_xy
        n = int(math.ceil(circumference / s))
        n = max(1, n)

        for i in range(n):
            theta = (2.0 * math.pi * i) / n
            x = math.cos(theta) * r_xy
            y = math.sin(theta) * r_xy
            pts.append((Vector((x, y, z)), None))

        phi += dphi

    return pts
