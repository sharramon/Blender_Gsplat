@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=C:\Chang\GSplat\Splats\Transformer_2"
set "OUTROOT=%ROOT%\outputs"
set "DATASET_NAME=colmap_data"
set "METHOD=splatfacto"

echo [0] starting gsplat_pipeline.bat
cd /d "%ROOT%"

rem --- wipe + recreate colmap_data ---
if exist "%DATASET_NAME%" rmdir /s /q "%DATASET_NAME%"
mkdir "%DATASET_NAME%"
mkdir "%DATASET_NAME%\images"

echo [0.1] copying images...
xcopy /e /i /y "images" "%DATASET_NAME%\images" >nul
if errorlevel 1 goto FAIL

rem --- COLMAP (assumes colmap is on PATH) ---
echo [1] running extractor...
colmap feature_extractor --database_path "%DATASET_NAME%\db_on.db" --image_path "%DATASET_NAME%\images" --ImageReader.single_camera 1 --ImageReader.camera_model OPENCV
echo [1.1] extractor done, errorlevel=%errorlevel%
if errorlevel 1 goto FAIL

echo [2] running matcher...
colmap exhaustive_matcher --database_path "%DATASET_NAME%\db_on.db"
echo [2.1] matcher done, errorlevel=%errorlevel%
if errorlevel 1 goto FAIL

echo [3] running mapper...
if not exist "%DATASET_NAME%\sparse_on" mkdir "%DATASET_NAME%\sparse_on"
colmap mapper --database_path "%DATASET_NAME%\db_on.db" --image_path "%DATASET_NAME%\images" --output_path "%DATASET_NAME%\sparse_on"
echo [3.1] mapper done, errorlevel=%errorlevel%
if errorlevel 1 goto FAIL

rem --- Conda activate nerfstudio env ---
echo [4] activating conda env: nerfstudio
call "%USERPROFILE%\miniconda3\Scripts\activate.bat"
if errorlevel 1 goto FAIL

call conda activate nerfstudio
if errorlevel 1 goto FAIL

echo [4.1] sanity check nerfstudio commands...
where ns-process-data >nul
if errorlevel 1 goto FAIL
where ns-train >nul
if errorlevel 1 goto FAIL
where ns-export >nul
if errorlevel 1 goto FAIL

rem --- Nerfstudio ---
echo [5] nerfstudio process-data...
ns-process-data images --data "%DATASET_NAME%" --output-dir "%DATASET_NAME%" --skip-colmap --skip-image-processing --colmap-model-path "sparse_on/0"
echo [5.1] ns-process-data done, errorlevel=%errorlevel%
if errorlevel 1 goto FAIL

echo [6] nerfstudio train (5000 iters)...
rem Use tensorboard to avoid viewer and avoid wandb prompts
ns-train %METHOD% --data "%DATASET_NAME%" --max-num-iterations 5000 --vis tensorboard
set "TRAIN_ERR=%errorlevel%"

echo [6.1] ns-train done, errorlevel=%TRAIN_ERR%
if not "%TRAIN_ERR%"=="0" goto FAIL

rem --- locate latest run (you confirmed it is here) ---
echo [7] locating latest run under: "%OUTROOT%\%DATASET_NAME%\%METHOD%"

set "RUN_DIR="
for /f "delims=" %%D in ('dir "%OUTROOT%\%DATASET_NAME%\%METHOD%" /b /ad /o-d 2^>nul') do (
  set "RUN_DIR=%OUTROOT%\%DATASET_NAME%\%METHOD%\%%D"
  goto GOT_RUN
)

:GOT_RUN
if "%RUN_DIR%"=="" (
  echo [X] Could not find any run folder under "%OUTROOT%\%DATASET_NAME%\%METHOD%"
  exit /b 1
)

set "CFG=%RUN_DIR%\config.yml"
echo [7.1] latest run: %RUN_DIR%

if not exist "%CFG%" (
  echo [X] Missing config: %CFG%
  exit /b 1
)

echo [8] exporting gaussian splat...
if not exist "%RUN_DIR%\export" mkdir "%RUN_DIR%\export"

rem Subcommand is version-dependent; your install appears to accept this.
ns-export gaussian-splat --load-config "%CFG%" --output-dir "%RUN_DIR%\export"
echo [8.1] ns-export done, errorlevel=%errorlevel%
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
  exit /b 1
)

copy /y "%EXPORTED_PLY%" "%ROOT%\FINAL_GSPLAT.ply" >nul
if errorlevel 1 goto FAIL

echo [OK] ALL DONE
echo     Run dir: %RUN_DIR%
echo     Exported: %EXPORTED_PLY%
echo     Final: %ROOT%\FINAL_GSPLAT.ply
pause
exit /b 0

:FAIL
echo [X] FAILED, errorlevel=%errorlevel%
pause
exit /b %errorlevel%
