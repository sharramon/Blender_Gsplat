import bpy
import os
import subprocess

from .utils import ensure_dir

class NSOT_OT_write_pipeline_bat(bpy.types.Operator):
    bl_idname = "nsot.write_pipeline_bat"
    bl_label = "Write Pipeline BAT (COLMAP + Train + Export)"
    bl_description = "Writes run_pipeline.bat into output_dir and launches it to run COLMAP, train, and export a .ply to the Output Directory"
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
where colmap >nul || (echo [X] colmap not found on PATH & goto FAIL)

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
ns-train %METHOD% --data "%DATASET_NAME%" --vis viewer --viewer.quit-on-train-completion True --max-num-iterations {MAX_ITERS}
set "TRAIN_ERR=%errorlevel%"
goto TRAIN_DONE

:TRAIN_HEADLESS
echo     viewer OFF
ns-train %METHOD% --data "%DATASET_NAME%" --vis tensorboard --max-num-iterations {MAX_ITERS}
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
        bat = bat.replace("{MAX_ITERS}", str(int(p.max_num_iterations)))

        with open(bat_path, "w", newline="\r\n", encoding="utf-8") as f:
            f.write(bat)
            
        
        subprocess.Popen(["cmd", "/c", "start", "", bat_path], cwd=out_root)

        self.report({"INFO"}, f"Wrote pipeline BAT: {bat_path}")
        return {"FINISHED"}


class NSOT_OT_write_export_bat(bpy.types.Operator):
    bl_idname = "nsot.write_export_bat"
    bl_label = "Write Export BAT (Export Latest)"
    bl_options = {"REGISTER"}
    bl_description = "Writes export_latest.bat into output_dir. Use when you want to 're-export' from the splat training."

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

set "ROOT=%~dp0."
set "OUTROOT=%ROOT%\outputs"
set "DATASET_NAME=colmap_data"
set "METHOD=splatfacto"

set "CONDA_BAT={CONDA_BAT}"
set "CONDA_ENV={CONDA_ENV}"

if not exist "%CONDA_BAT%" (
  echo [X] conda.bat not found: %CONDA_BAT%
  goto FAIL
)

echo [0] activating conda env: %CONDA_ENV%
call "%CONDA_BAT%" activate "%CONDA_ENV%"
if errorlevel 1 goto FAIL

where ns-export >nul || (echo [X] ns-export not found in PATH & goto FAIL)

echo [7] locating latest run under: "%OUTROOT%\%DATASET_NAME%\%METHOD%"

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

echo [8] exporting gaussian splat...
if not exist "%RUN_DIR%\export" mkdir "%RUN_DIR%\export"
ns-export gaussian-splat --load-config "%CFG%" --output-dir "%RUN_DIR%\export"
if errorlevel 1 goto FAIL

echo [9] copying exported .ply to project root as FINAL_GSPLAT.ply
if exist "%ROOT%\FINAL_GSPLAT.ply" del /q "%ROOT%\FINAL_GSPLAT.ply"

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

copy /y "%EXPORTED_PLY%" "%ROOT%\FINAL_GSPLAT.ply" >nul
if errorlevel 1 goto FAIL

echo [OK] EXPORT DONE
echo     Final: %ROOT%\FINAL_GSPLAT.ply
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
            
        
        subprocess.Popen(["cmd", "/c", "start", "", bat_path], cwd=out_root)

        self.report({"INFO"}, f"Wrote export BAT: {bat_path}")
        return {"FINISHED"}
