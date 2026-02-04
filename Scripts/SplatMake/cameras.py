import bpy
from mathutils import Vector, Matrix

from .utils import (
    get_or_create_collection,
    spherical_points_by_spacing,
    look_at_matrix,
)

def make_camera(name: str, mw: Matrix, lens_mm: float, sensor_w: float, clip_start: float, clip_end: float):
    cam_data = bpy.data.cameras.new(name=name + "_DATA")
    cam_data.lens = lens_mm
    cam_data.sensor_width = sensor_w
    cam_obj = bpy.data.objects.new(name, cam_data)
    cam_obj.matrix_world = mw
    cam_obj.data.clip_start = clip_start
    cam_obj.data.clip_end = clip_end
    return cam_obj

def clear_prefixed_cameras(collection, prefix: str):
    import bpy
    remove = [obj for obj in list(collection.objects) if obj.type == "CAMERA" and obj.name.startswith(prefix)]
    for obj in remove:
        bpy.data.objects.remove(obj, do_unlink=True)

def get_layer_scales(p):
    if not p.use_radius_layers:
        return [1.0]

    scales = []
    for i in range(1, int(p.layer_count) + 1):
        v = float(getattr(p, f"layer_scale_{i:02d}", 0.0))
        if v > 0.0:
            scales.append(v)

    return scales if scales else [1.0]

class NSOT_OT_create_cameras(bpy.types.Operator):
    bl_idname = "nsot.create_cameras"
    bl_label = "Create Cameras (Spherical)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        p = context.scene.nsot_props
        coll = get_or_create_collection(p.collection_name)
        clear_prefixed_cameras(coll, p.name_prefix)

        target = Vector((p.target_x, p.target_y, p.target_z))
        up = Vector((p.up_x, p.up_y, p.up_z))
        if up.length < 1e-8:
            up = Vector((0.0, 0.0, 1.0))
        up.normalize()

        scales = get_layer_scales(p)

        total = 0
        for layer_idx, scale in enumerate(scales):
            layer_radius = p.radius * scale
            pts = spherical_points_by_spacing(p.max_dist, layer_radius)

            idx = 0
            for local_pos, tag in pts:
                world_pos = target + local_pos

                base = f"{p.name_prefix}L{layer_idx:02d}_{idx:03d}"
                if tag == "BOTTOM":
                    name = base + "_BOTTOM"
                elif tag == "TOP":
                    name = base + "_TOP"
                else:
                    name = base

                mw = look_at_matrix(world_pos, target, up)
                cam = make_camera(name, mw, p.focal_mm, p.sensor_width_mm, p.clip_start, p.clip_end)
                coll.objects.link(cam)
                idx += 1

            total += idx

        self.report({"INFO"}, f"Created {total} cameras across {len(scales)} layer(s) in '{p.collection_name}'")
        return {"FINISHED"}
