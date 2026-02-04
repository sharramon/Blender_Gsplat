import bpy

class NSOT_PT_panel(bpy.types.Panel):
    bl_label = "Nerfstudio Export"
    bl_idname = "NSOT_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Nerfstudio"

    def draw(self, context):
        layout = self.layout
        p = context.scene.nsot_props

        layout.prop(p, "output_dir")
        layout.prop(p, "collection_name")
        layout.prop(p, "name_prefix")

        layout.separator()
        layout.label(text="Spherical Rig")
        layout.prop(p, "radius")
        layout.prop(p, "max_dist")

        layout.separator()
        layout.label(text="Radius Layers")
        layout.prop(p, "use_radius_layers")

        if p.use_radius_layers:
            layout.prop(p, "layer_count")
            layer_count = int(p.layer_count)
            for i in range(1, layer_count + 1):
                layout.prop(p, f"layer_scale_{i:02d}")

        layout.separator()
        layout.label(text="Look At Target")
        col = layout.column(align=True)
        col.prop(p, "target_x")
        col.prop(p, "target_y")
        col.prop(p, "target_z")

        layout.separator()
        layout.label(text="Up Vector")
        col = layout.column(align=True)
        col.prop(p, "up_x")
        col.prop(p, "up_y")
        col.prop(p, "up_z")

        layout.separator()
        layout.label(text="Camera Intrinsics")
        layout.prop(p, "focal_mm")
        layout.prop(p, "sensor_width_mm")
        layout.prop(p, "clip_start")
        layout.prop(p, "clip_end")

        layout.separator()
        layout.label(text="Render")
        layout.prop(p, "engine")
        layout.prop(p, "res_x")
        layout.prop(p, "res_y")
        layout.prop(p, "png_compression")
        if p.engine == "CYCLES":
            layout.prop(p, "cycles_samples")
            layout.prop(p, "cycles_denoise")
        layout.prop(p, "film_transparent")

        layout.separator()
        layout.label(text="Progress")
        if p.is_rendering:
            layout.label(text=f"Rendering: {p.progress_current} / {p.progress_total}")
        elif p.progress_total > 0:
            layout.label(text=f"Last Render: {p.progress_total} images")

        layout.separator()
        layout.operator("nsot.create_cameras", text="Create Cameras", icon="CAMERA_DATA")
        layout.operator("nsot.export_dataset", text="Render Images", icon="RENDER_STILL")

        layout.separator()
        layout.label(text="Pipeline (External)")
        layout.prop(p, "conda_bat")
        layout.prop(p, "conda_env")
        layout.prop(p, "max_num_iterations")
        layout.prop(p, "open_viewer")
        layout.operator("nsot.write_pipeline_bat", text="Get Splat(COLMAP + Splat + Export)", icon="FILE_SCRIPT")
        layout.operator("nsot.write_export_bat", text="Export Latest", icon="EXPORT")
