import bpy
import os

from .utils import ensure_dir, set_render_settings

class NSOT_OT_export_dataset(bpy.types.Operator):
    bl_idname = "nsot.export_dataset"
    bl_label = "Render + Export (Images Only)"
    bl_options = {"REGISTER"}

    def execute(self, context):
        p = context.scene.nsot_props

        if not p.output_dir:
            self.report({"ERROR"}, "Output Directory is empty.")
            return {"CANCELLED"}

        out_root = bpy.path.abspath(p.output_dir)
        out_images = os.path.join(out_root, "images")
        ensure_dir(out_images)

        scene = context.scene
        set_render_settings(
            scene,
            p.engine,
            p.res_x,
            p.res_y,
            p.png_compression,
            p.film_transparent,
            p.cycles_samples,
            p.cycles_denoise,
        )

        coll = bpy.data.collections.get(p.collection_name)
        if coll is None:
            self.report({"ERROR"}, f"Collection '{p.collection_name}' not found. Create cameras first.")
            return {"CANCELLED"}

        cams = sorted(
            [obj for obj in coll.objects if obj.type == "CAMERA" and obj.name.startswith(p.name_prefix)],
            key=lambda o: o.name,
        )
        if not cams:
            self.report({"ERROR"}, f"No cameras with prefix '{p.name_prefix}' in '{p.collection_name}'.")
            return {"CANCELLED"}

        wm = context.window_manager
        p.progress_total = len(cams)
        p.progress_current = 0
        p.is_rendering = True

        wm.progress_begin(0, len(cams))
        try:
            for i, cam in enumerate(cams, start=1):
                filename = f"{cam.name}.png"
                img_abs = os.path.join(out_images, filename)

                scene.camera = cam
                scene.render.filepath = img_abs

                p.progress_current = i
                wm.progress_update(i)
                bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)

                bpy.ops.render.render(write_still=True)
        finally:
            wm.progress_end()
            p.is_rendering = False

        self.report({"INFO"}, f"Exported {len(cams)} images to {out_images}")
        return {"FINISHED"}
