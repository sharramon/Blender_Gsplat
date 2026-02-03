bl_info = {
    "name": "Nerfstudio Object-Only Splat Exporter (Spherical) [Images Only + Pipeline Scripts]",
    "author": "ChatGPT",
    "version": (1, 8, 3),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar (N) > Nerfstudio",
    "description": "Create spherical camera rig(s) with optional radius layers and render RGBA PNGs to an images/ folder. Optionally write external COLMAP+Nerfstudio pipeline scripts.",
    "category": "Import-Export",
}

import bpy
import os
import math
import subprocess
from mathutils import Vector, Matrix


def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def get_or_create_collection(name: str):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def clear_prefixed_cameras(coll, prefix: str):
    remove = [obj for obj in list(coll.objects) if obj.type == "CAMERA" and obj.name.startswith(prefix)]
    for obj in remove:
        bpy.data.objects.remove(obj, do_unlink=True)


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


def make_camera(name: str, mw: Matrix, lens_mm: float, sensor_w: float, clip_start: float, clip_end: float):
    cam_data = bpy.data.cameras.new(name=name + "_DATA")
    cam_data.lens = lens_mm
    cam_data.sensor_width = sensor_w
    cam_obj = bpy.data.objects.new(name, cam_data)
    cam_obj.matrix_world = mw
    cam_obj.data.clip_start = clip_start
    cam_obj.data.clip_end = clip_end
    return cam_obj


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


class NSOT_Props(bpy.types.PropertyGroup):
    output_dir: bpy.props.StringProperty(name="Output Directory", subtype="DIR_PATH", default="")

    collection_name: bpy.props.StringProperty(name="Camera Collection", default="SphereCams")
    name_prefix: bpy.props.StringProperty(name="Camera Name Prefix", default="SphereCam_")

    engine: bpy.props.EnumProperty(
        name="Render Engine",
        items=[("CYCLES", "Cycles", ""), ("BLENDER_EEVEE_NEXT", "Eevee", "")],
        default="CYCLES",
    )

    res_x: bpy.props.IntProperty(name="Resolution X", default=1920, min=16)
    res_y: bpy.props.IntProperty(name="Resolution Y", default=1080, min=16)
    png_compression: bpy.props.IntProperty(name="PNG Compression", default=15, min=0, max=100)

    cycles_samples: bpy.props.IntProperty(name="Cycles Samples", default=128, min=1)
    cycles_denoise: bpy.props.BoolProperty(name="Cycles Denoise", default=True)
    film_transparent: bpy.props.BoolProperty(name="Transparent Film", default=True)

    focal_mm: bpy.props.FloatProperty(name="Focal (mm)", default=35.0, min=1.0)
    sensor_width_mm: bpy.props.FloatProperty(name="Sensor Width (mm)", default=36.0, min=1.0)
    clip_start: bpy.props.FloatProperty(name="Clip Start", default=0.01, min=0.0001)
    clip_end: bpy.props.FloatProperty(name="Clip End", default=1000.0, min=0.1)

    target_x: bpy.props.FloatProperty(name="Target X", default=0.0)
    target_y: bpy.props.FloatProperty(name="Target Y", default=0.0)
    target_z: bpy.props.FloatProperty(name="Target Z", default=0.0)

    up_x: bpy.props.FloatProperty(name="Up X", default=0.0)
    up_y: bpy.props.FloatProperty(name="Up Y", default=0.0)
    up_z: bpy.props.FloatProperty(name="Up Z", default=1.0)

    radius: bpy.props.FloatProperty(name="Sphere Radius", default=5.0, min=0.001)
    max_dist: bpy.props.FloatProperty(name="Max Camera Spacing", default=0.6, min=0.001)

    use_radius_layers: bpy.props.BoolProperty(
        name="Use Radius Layers",
        default=False,
        description="If enabled, create multiple concentric camera spheres using the layer scales below.",
    )

    layer_count: bpy.props.IntProperty(
        name="Layer Count",
        default=1,
        min=1,
        max=10,
        description="How many radius layers to use (1-10). Each layer uses Sphere Radius * Layer Scale N.",
    )

    layer_scale_01: bpy.props.FloatProperty(name="Layer 1 Scale", default=1.0, min=0.0, precision=3)
    layer_scale_02: bpy.props.FloatProperty(name="Layer 2 Scale", default=0.5, min=0.0, precision=3)
    layer_scale_03: bpy.props.FloatProperty(name="Layer 3 Scale", default=0.2, min=0.0, precision=3)
    layer_scale_04: bpy.props.FloatProperty(name="Layer 4 Scale", default=0.0, min=0.0, precision=3)
    layer_scale_05: bpy.props.FloatProperty(name="Layer 5 Scale", default=0.0, min=0.0, precision=3)
    layer_scale_06: bpy.props.FloatProperty(name="Layer 6 Scale", default=0.0, min=0.0, precision=3)
    layer_scale_07: bpy.props.FloatProperty(name="Layer 7 Scale", default=0.0, min=0.0, precision=3)
    layer_scale_08: bpy.props.FloatProperty(name="Layer 8 Scale", default=0.0, min=0.0, precision=3)
    layer_scale_09: bpy.props.FloatProperty(name="Layer 9 Scale", default=0.0, min=0.0, precision=3)
    layer_scale_10: bpy.props.FloatProperty(name="Layer 10 Scale", default=0.0, min=0.0, precision=3)

    is_rendering: bpy.props.BoolProperty(name="Is Rendering", default=False)
    progress_current: bpy.props.IntProperty(name="Progress Current", default=0, min=0)
    progress_total: bpy.props.IntProperty(name="Progress Total", default=0, min=0)

    # These are still shown in the UI for now (not wired into the new BATs directly)
    conda_bat: bpy.props.StringProperty(
        name="CONDA_BAT Path",
        subtype="FILE_PATH",
        default=r"C:\Users\admin\miniconda3\condabin\conda.bat",
        description="Path to conda.bat (e.g. Miniconda/Anaconda condabin\\conda.bat).",
    )

    conda_env: bpy.props.StringProperty(
        name="CONDA_ENV Name",
        default="nerfstudio",
        description="Conda environment name that contains nerfstudio + ns-* commands.",
    )

    open_viewer: bpy.props.BoolProperty(
        name="Open Viewer (localhost:7007)",
        default=True,
        description="(Legacy) Viewer toggle; current run_pipeline.bat uses default ns-train viewer.",
    )


def _get_layer_scales(p: NSOT_Props):
    if not p.use_radius_layers:
        return [1.0]

    scales = []
    for i in range(1, int(p.layer_count) + 1):
        v = float(getattr(p, f"layer_scale_{i:02d}", 0.0))
        if v > 0.0:
            scales.append(v)

    if not scales:
        scales = [1.0]
    return scales


class NSOT_OT_create_cameras(bpy.types.Operator):
    bl_idname = "nsot.create_cameras"
    bl_label = "Create Cameras (Spherical, Top+Bottom)"
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

        scales = _get_layer_scales(p)

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


class NSOT_OT_write_pipeline_bat(bpy.types.Operator):
    bl_idname = "nsot.write_pipeline_bat"
    bl_label = "Write Pipeline BAT (COLMAP + Train)"
    bl_options = {"REGISTER"}

    def execute(self, context):
        p = context.scene.nsot_props
        if not p.output_dir:
            self.report({"ERROR"}, "Output Directory is empty.")
            return {"CANCELLED"}

        out_root = bpy.path.abspath(p.output_dir)
        ensure_dir(out_root)

        bat_path = os.path.join(out_root, "run_pipeline.bat")

        bat = r"""@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
set "OUTROOT=%ROOT%outputs"
set "DATASET_NAME=colmap_data"
set "METHOD=splatfacto"

set "CONDA_BAT={CONDA_BAT}"
set "CONDA_ENV={CONDA_ENV}"
set "OPEN_VIEWER={OPEN_VIEWER}"

cd /d "%ROOT%"

if not exist "%CONDA_BAT%" (
  echo [X] conda.bat not found: %CONDA_BAT%
  goto FAIL
)

echo [0] activating conda env: %CONDA_ENV%
call "%CONDA_BAT%" activate "%CONDA_ENV%"
if errorlevel 1 goto FAIL

where ns-process-data >nul || (echo [X] ns-process-data not found & goto FAIL)
where ns-train >nul || (echo [X] ns-train not found & goto FAIL)
where ns-export >nul || (echo [X] ns-export not found & goto FAIL)

echo [0.1] reset dataset folder
if exist "%DATASET_NAME%" rmdir /s /q "%DATASET_NAME%"
mkdir "%DATASET_NAME%"
mkdir "%DATASET_NAME%\images"

echo [0.2] copying images...
xcopy /e /i /y "images" "%DATASET_NAME%\images" >nul
if errorlevel 1 goto FAIL

echo [1] colmap feature_extractor...
call colmap feature_extractor --database_path "%DATASET_NAME%\db_on.db" --image_path "%DATASET_NAME%\images" --ImageReader.single_camera 1 --ImageReader.camera_model OPENCV
if errorlevel 1 goto FAIL

echo [2] colmap exhaustive_matcher...
call colmap exhaustive_matcher --database_path "%DATASET_NAME%\db_on.db"
if errorlevel 1 goto FAIL

echo [3] colmap mapper...
if not exist "%DATASET_NAME%\sparse_on" mkdir "%DATASET_NAME%\sparse_on"
call colmap mapper --database_path "%DATASET_NAME%\db_on.db" --image_path "%DATASET_NAME%\images" --output_path "%DATASET_NAME%\sparse_on"
if errorlevel 1 goto FAIL

echo [4] nerfstudio process-data...
ns-process-data images --data "%DATASET_NAME%" --output-dir "%DATASET_NAME%" --skip-colmap --skip-image-processing --colmap-model-path "sparse_on/0"
if errorlevel 1 goto FAIL

echo [5] training... OPEN_VIEWER=%OPEN_VIEWER%
if "%OPEN_VIEWER%"=="1" goto TRAIN_VIEWER
goto TRAIN_HEADLESS

:TRAIN_VIEWER
echo     viewer ON, will open browser when port 7007 is ready
start "" /b powershell -NoProfile -Command "$deadline=(Get-Date).AddSeconds(120); while((Get-Date) -lt $deadline){ try { $c=New-Object Net.Sockets.TcpClient('127.0.0.1',7007); $c.Close(); Start-Process 'http://127.0.0.1:7007'; break } catch { Start-Sleep -Milliseconds 250 } }"
ns-train %METHOD% --data "%DATASET_NAME%" --vis viewer --viewer.quit-on-train-completion True
set "TRAIN_ERR=%errorlevel%"
goto TRAIN_DONE

:TRAIN_HEADLESS
echo     viewer OFF
ns-train %METHOD% --data "%DATASET_NAME%" --vis tensorboard
set "TRAIN_ERR=%errorlevel%"
goto TRAIN_DONE

:TRAIN_DONE
echo [5.1] ns-train done, errorlevel=%TRAIN_ERR%
if not "%TRAIN_ERR%"=="0" goto FAIL

echo [6] locating latest run under: "%OUTROOT%\%DATASET_NAME%\%METHOD%"
set "RUN_DIR="
for /f "delims=" %%D in ('dir "%OUTROOT%\%DATASET_NAME%\%METHOD%" /b /ad /o-d 2^>nul') do (
  set "RUN_DIR=%OUTROOT%\%DATASET_NAME%\%METHOD%\%%D"
  goto GOT_RUN
)

:GOT_RUN
if "%RUN_DIR%"=="" (
  echo [X] Could not find any run folder under "%OUTROOT%\%DATASET_NAME%\%METHOD%"
  goto FAIL
)

set "CFG=%RUN_DIR%\config.yml"
if not exist "%CFG%" (
  echo [X] Missing config: %CFG%
  goto FAIL
)

echo [7] exporting gaussian splat...
if not exist "%RUN_DIR%\export" mkdir "%RUN_DIR%\export"
ns-export gaussian-splat --load-config "%CFG%" --output-dir "%RUN_DIR%\export"
if errorlevel 1 goto FAIL

echo [8] copying exported .ply to project root as FINAL_GSPLAT.ply
if exist "%ROOT%FINAL_GSPLAT.ply" del /q "%ROOT%FINAL_GSPLAT.ply"

set "EXPORTED_PLY="
for /f "delims=" %%F in ('dir "%RUN_DIR%\export" /b /s "*.ply" 2^>nul') do (
  set "EXPORTED_PLY=%%F"
  goto GOT_PLY
)

:GOT_PLY
if "%EXPORTED_PLY%"=="" (
  echo [X] No .ply found under "%RUN_DIR%\export"
  goto FAIL
)

copy /y "%EXPORTED_PLY%" "%ROOT%FINAL_GSPLAT.ply" >nul
if errorlevel 1 goto FAIL

echo [OK] ALL DONE
echo     Final: %ROOT%FINAL_GSPLAT.ply
pause
exit /b 0

:FAIL
echo [X] FAILED, errorlevel=%errorlevel%
pause
exit /b %errorlevel%
"""

        bat = bat.replace("{CONDA_BAT}", p.conda_bat)
        bat = bat.replace("{CONDA_ENV}", p.conda_env)
        bat = bat.replace("{OPEN_VIEWER}", "1" if p.open_viewer else "0")

        with open(bat_path, "w", newline="\r\n", encoding="utf-8") as f:
            f.write(bat)

        subprocess.Popen(["cmd", "/c", "start", "", bat_path], cwd=out_root)

        self.report({"INFO"}, f"Wrote pipeline BAT: {bat_path}")
        return {"FINISHED"}

    
class NSOT_OT_write_export_bat(bpy.types.Operator):
    bl_idname = "nsot.write_export_bat"
    bl_label = "Write Export BAT (Export Latest)"
    bl_options = {"REGISTER"}

    def execute(self, context):
        p = context.scene.nsot_props
        if not p.output_dir:
            self.report({"ERROR"}, "Output Directory is empty.")
            return {"CANCELLED"}

        out_root = bpy.path.abspath(p.output_dir)
        ensure_dir(out_root)

        bat_path = os.path.join(out_root, "export_latest.bat")

        bat = r"""@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ROOT = folder containing this .bat
set "ROOT=%~dp0"
set "OUTROOT=%ROOT%outputs"
set "DATASET_NAME=colmap_data"
set "METHOD=splatfacto"

rem --- Conda activate nerfstudio env ---
set "CONDA_BAT={CONDA_BAT}"
set "CONDA_ENV={CONDA_ENV}"

if not exist "%CONDA_BAT%" (
  echo [X] conda.bat not found: %CONDA_BAT%
  goto FAIL
)

echo [0] activating conda env: %CONDA_ENV%
call "%CONDA_BAT%" activate "%CONDA_ENV%"
if errorlevel 1 goto FAIL

where ns-export >nul
if errorlevel 1 (
  echo [X] ns-export not found in PATH. Is nerfstudio installed in %CONDA_ENV%?
  goto FAIL
)

echo [7] locating latest run under: "%OUTROOT%\%DATASET_NAME%\%METHOD%"

set "RUN_DIR="
for /f "delims=" %%D in ('dir "%OUTROOT%\%DATASET_NAME%\%METHOD%" /b /ad /o-d 2^>nul') do (
  set "RUN_DIR=%OUTROOT%\%DATASET_NAME%\%METHOD%\%%D"
  goto GOT_RUN
)

:GOT_RUN
if "%RUN_DIR%"=="" (
  echo [X] Could not find any run folder under "%OUTROOT%\%DATASET_NAME%\%METHOD%"
  pause
  exit /b 1
)

set "CFG=%RUN_DIR%\config.yml"
echo [7.1] latest run: %RUN_DIR%

if not exist "%CFG%" (
  echo [X] Missing config: %CFG%
  pause
  exit /b 1
)

echo [8] exporting gaussian splat...
if not exist "%RUN_DIR%\export" mkdir "%RUN_DIR%\export"

ns-export gaussian-splat --load-config "%CFG%" --output-dir "%RUN_DIR%\export"
echo [8.1] ns-export done, errorlevel=%errorlevel%
if errorlevel 1 goto FAIL

echo [9] copying exported .ply to project root as FINAL_GSPLAT.ply
if exist "%ROOT%FINAL_GSPLAT.ply" del /q "%ROOT%FINAL_GSPLAT.ply"

set "EXPORTED_PLY="
for /f "delims=" %%F in ('dir "%RUN_DIR%\export" /b /s "*.ply" 2^>nul') do (
  set "EXPORTED_PLY=%%F"
  goto GOT_PLY
)

:GOT_PLY
if "%EXPORTED_PLY%"=="" (
  echo [X] No .ply found under "%RUN_DIR%\export"
  pause
  exit /b 1
)

copy /y "%EXPORTED_PLY%" "%ROOT%FINAL_GSPLAT.ply" >nul
if errorlevel 1 goto FAIL

echo [OK] EXPORT DONE
echo     Run dir: %RUN_DIR%
echo     Exported: %EXPORTED_PLY%
echo     Final: %ROOT%FINAL_GSPLAT.ply
pause
exit /b 0

:FAIL
echo [X] FAILED, errorlevel=%errorlevel%
pause
exit /b %errorlevel%
"""

        bat = bat.replace("{CONDA_BAT}", p.conda_bat)
        bat = bat.replace("{CONDA_ENV}", p.conda_env)

        with open(bat_path, "w", newline="\r\n", encoding="utf-8") as f:
            f.write(bat)

        self.report({"INFO"}, f"Wrote export BAT: {bat_path}")
        return {"FINISHED"}



class NSOT_PT_panel(bpy.types.Panel):
    bl_label = "Nerfstudio Export"
    bl_idname = "NSOT_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Nerfstudio"

    def draw(self, context):
        p = context.scene.nsot_props
        layout = self.layout

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
            for i in range(1, int(p.layer_count) + 1):
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
        layout.operator(NSOT_OT_create_cameras.bl_idname, icon="CAMERA_DATA")
        layout.operator(NSOT_OT_export_dataset.bl_idname, icon="RENDER_STILL")

        layout.separator()
        layout.label(text="Pipeline (External)")
        layout.prop(p, "conda_bat")
        layout.prop(p, "conda_env")
        layout.prop(p, "open_viewer")
        layout.operator(NSOT_OT_write_pipeline_bat.bl_idname, icon="FILE_SCRIPT")
        layout.operator(NSOT_OT_write_export_bat.bl_idname, icon="EXPORT")
classes = (
    NSOT_Props,
    NSOT_OT_create_cameras,
    NSOT_OT_export_dataset,
    NSOT_OT_write_pipeline_bat,
    NSOT_OT_write_export_bat,
    NSOT_PT_panel,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.nsot_props = bpy.props.PointerProperty(type=NSOT_Props)


def unregister():
    del bpy.types.Scene.nsot_props
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
