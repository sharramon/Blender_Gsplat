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
call colmap feature_extractor ^
  --database_path "%DATASET_NAME%\db_on.db" ^
  --image_path "%DATASET_NAME%\images" ^
  --ImageReader.single_camera 1 ^
  --ImageReader.camera_model OPENCV
echo [1.1] extractor done, errorlevel=%errorlevel%
if errorlevel 1 goto FAIL

echo [2] running matcher...
call colmap exhaustive_matcher --database_path "%DATASET_NAME%\db_on.db"
echo [2.1] matcher done, errorlevel=%errorlevel%
if errorlevel 1 goto FAIL

echo [3] running mapper...
if not exist "%DATASET_NAME%\sparse_on" mkdir "%DATASET_NAME%\sparse_on"
call colmap mapper ^
  --database_path "%DATASET_NAME%\db_on.db" ^
  --image_path "%DATASET_NAME%\images" ^
  --output_path "%DATASET_NAME%\sparse_on"
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
ns-process-data images ^
  --data "%DATASET_NAME%" ^
  --output-dir "%DATASET_NAME%" ^
  --skip-colmap ^
  --skip-image-processing ^
  --colmap-model-path "sparse_on/0"
echo [5.1] ns-process-data done, errorlevel=%errorlevel%
if errorlevel 1 goto FAIL

echo [6] nerfstudio train (5000 iters)...
ns-train %METHOD% ^
  --data "%DATASET_NAME%" ^
  --max-num-iterations 5000 ^
  --vis tensorboard
set "TRAIN_ERR=%errorlevel%"

echo [6.1] ns-train done, errorlevel=%TRAIN_ERR%
if not "%TRAIN_ERR%"=="0" goto FAIL

rem --- locate latest run ---
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
  echo [X] Missing config
