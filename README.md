# Blender_Gsplat

Blender add-on for converting existing 3D models into Gaussian Splats using synthetic renders, COLMAP, and Nerfstudio.
Designed for fast iteration and asset reuse, without real-world capture.

## What This Does

This add-on generates a spherical, multi-layer camera rig around a 3D object, renders object-only RGBA images, and creates a one-click pipeline script that runs:

* COLMAP feature extraction and mapping
* Nerfstudio process-data
* Splatfacto training
* Final `.ply` Gaussian Splat export

Typical result: a ~25 MB mesh compresses down to ~9 MB, suitable for web viewers and lightweight pipelines.

## Requirements

### Nerfstudio

Follow the official setup instructions:
[https://github.com/nerfstudio-project/gsplat](https://github.com/nerfstudio-project/gsplat)

Ensure the following are available in your environment:

* `ns-process-data`
* `ns-train`
* COLMAP

### Blender

Tested with **Blender 4.4.3**.

Install the add-on via:

Edit → Preferences → Add-ons → Install from Disk → `SplatMake.zip`

Enable the add-on after installation.

## Basic Workflow

1. Import or open your 3D model in Blender
2. Select the object you want to convert
3. Generate cameras using the add-on panel
4. Render images
5. Run the generated pipeline script

## Add-on Panel Overview

### Generate Cameras

Creates a spherical camera distribution around the selected object.
Supports multiple radius layers and spacing-based density so coverage scales automatically with object size.

### Render Images

Renders object-only RGBA images with a transparent background.
Images are saved to an `images/` directory, ready for COLMAP processing.

### Generate Pipeline Script

Creates a Windows `.bat` file that runs the full external pipeline:

COLMAP → Nerfstudio → Splatfacto → final `.ply` export

### Run Pipeline

Launches the generated script directly.
The final output is copied to `FINAL_GSPLAT.ply` for easy access.

## Output Structure

* Rendered images: `images/`
* COLMAP and Nerfstudio data: `colmap_data/`, `nerfstudio/`
* Final Gaussian Splat: `FINAL_GSPLAT.ply`

## Notes

* This pipeline assumes clean geometry and reasonable materials.
* For best results, center and scale the object before generating cameras.
* Very small or extremely large objects may require adjusting camera spacing or radius layers.
