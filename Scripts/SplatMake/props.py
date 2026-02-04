import bpy
from bpy.props import (
    StringProperty,
    IntProperty,
    FloatProperty,
    BoolProperty,
    EnumProperty,
)

class NSOT_Props(bpy.types.PropertyGroup):
    output_dir: StringProperty(name="Output Directory", subtype="DIR_PATH", default="")

    collection_name: StringProperty(name="Camera Collection", default="SphereCams")
    name_prefix: StringProperty(name="Camera Name Prefix", default="SphereCam_")

    engine: EnumProperty(
        name="Render Engine",
        items=[("CYCLES", "Cycles", ""), ("BLENDER_EEVEE_NEXT", "Eevee", "")],
        default="CYCLES",
    )

    res_x: IntProperty(name="Resolution X", default=1920, min=16)
    res_y: IntProperty(name="Resolution Y", default=1080, min=16)
    png_compression: IntProperty(name="PNG Compression", default=15, min=0, max=100)

    cycles_samples: IntProperty(name="Cycles Samples", default=128, min=1)
    cycles_denoise: BoolProperty(name="Cycles Denoise", default=True)
    film_transparent: BoolProperty(name="Transparent Film", default=True)

    focal_mm: FloatProperty(name="Focal (mm)", default=35.0, min=1.0)
    sensor_width_mm: FloatProperty(name="Sensor Width (mm)", default=36.0, min=1.0)
    clip_start: FloatProperty(name="Clip Start", default=0.01, min=0.0001)
    clip_end: FloatProperty(name="Clip End", default=1000.0, min=0.1)

    target_x: FloatProperty(name="Target X", default=0.0)
    target_y: FloatProperty(name="Target Y", default=0.0)
    target_z: FloatProperty(name="Target Z", default=0.0)

    up_x: FloatProperty(name="Up X", default=0.0)
    up_y: FloatProperty(name="Up Y", default=0.0)
    up_z: FloatProperty(name="Up Z", default=1.0)

    radius: FloatProperty(name="Sphere Radius", default=5.0, min=0.001)
    max_dist: FloatProperty(name="Max Camera Spacing", default=0.6, min=0.001)

    use_radius_layers: BoolProperty(
        name="Use Radius Layers",
        default=False,
        description="If enabled, create multiple concentric camera spheres using the layer scales below.",
    )

    layer_count: IntProperty(
        name="Layer Count",
        default=1,
        min=1,
        max=10,
        description="How many radius layers to use (1-10). Each layer uses Sphere Radius * Layer Scale N.",
    )

    layer_scale_01: FloatProperty(name="Layer 1 Scale", default=1.0, min=0.0, precision=3)
    layer_scale_02: FloatProperty(name="Layer 2 Scale", default=0.5, min=0.0, precision=3)
    layer_scale_03: FloatProperty(name="Layer 3 Scale", default=0.2, min=0.0, precision=3)
    layer_scale_04: FloatProperty(name="Layer 4 Scale", default=0.0, min=0.0, precision=3)
    layer_scale_05: FloatProperty(name="Layer 5 Scale", default=0.0, min=0.0, precision=3)
    layer_scale_06: FloatProperty(name="Layer 6 Scale", default=0.0, min=0.0, precision=3)
    layer_scale_07: FloatProperty(name="Layer 7 Scale", default=0.0, min=0.0, precision=3)
    layer_scale_08: FloatProperty(name="Layer 8 Scale", default=0.0, min=0.0, precision=3)
    layer_scale_09: FloatProperty(name="Layer 9 Scale", default=0.0, min=0.0, precision=3)
    layer_scale_10: FloatProperty(name="Layer 10 Scale", default=0.0, min=0.0, precision=3)

    is_rendering: BoolProperty(name="Is Rendering", default=False)
    progress_current: IntProperty(name="Progress Current", default=0, min=0)
    progress_total: IntProperty(name="Progress Total", default=0, min=0)

    conda_bat: StringProperty(
        name="CONDA_BAT Path",
        subtype="FILE_PATH",
        default=r"C:\Users\admin\miniconda3\condabin\conda.bat",
        description="Path to conda.bat (Miniconda/Anaconda condabin\\conda.bat).",
    )

    conda_env: StringProperty(
        name="CONDA_ENV Name",
        default="nerfstudio",
        description="Conda environment name that contains nerfstudio + ns-* commands.",
    )
    
    max_num_iterations: IntProperty(
        name="Max Iterations",
        default=5000,
        min=1,
        description="Max training iterations for ns-train.",
    )


    open_viewer: BoolProperty(
        name="Open Viewer (localhost:7007)",
        default=True,
        description="Open nerfstudio viewer and auto-open browser; also auto-export after training completes.",
    )
