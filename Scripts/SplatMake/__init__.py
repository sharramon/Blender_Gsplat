bl_info = {
    "name": "Nerfstudio Object-Only Splat Exporter (Spherical) [Images Only + Pipeline Scripts]",
    "author": "ChatGPT",
    "version": (1, 8, 4),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar (N) > Nerfstudio",
    "description": "Create spherical camera rigs and render RGBA PNGs to images/. Optionally write COLMAP+Nerfstudio BATs.",
    "category": "Import-Export",
}

import bpy

from .props import NSOT_Props
from .cameras import NSOT_OT_create_cameras
from .render_images import NSOT_OT_export_dataset
from .pipeline import NSOT_OT_write_pipeline_bat, NSOT_OT_write_export_bat
from .ui import NSOT_PT_panel

_classes = (
    NSOT_Props,
    NSOT_OT_create_cameras,
    NSOT_OT_export_dataset,
    NSOT_OT_write_pipeline_bat,
    NSOT_OT_write_export_bat,
    NSOT_PT_panel,
)

def register():
    bpy.utils.register_class(NSOT_Props)
    bpy.types.Scene.nsot_props = bpy.props.PointerProperty(type=NSOT_Props)

    bpy.utils.register_class(NSOT_OT_create_cameras)
    bpy.utils.register_class(NSOT_OT_export_dataset)
    bpy.utils.register_class(NSOT_OT_write_pipeline_bat)
    bpy.utils.register_class(NSOT_OT_write_export_bat)
    bpy.utils.register_class(NSOT_PT_panel)

def unregister():
    bpy.utils.unregister_class(NSOT_PT_panel)
    bpy.utils.unregister_class(NSOT_OT_write_export_bat)
    bpy.utils.unregister_class(NSOT_OT_write_pipeline_bat)
    bpy.utils.unregister_class(NSOT_OT_export_dataset)
    bpy.utils.unregister_class(NSOT_OT_create_cameras)

    del bpy.types.Scene.nsot_props
    bpy.utils.unregister_class(NSOT_Props)

