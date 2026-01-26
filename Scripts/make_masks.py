# make_masks.py
import argparse
from pathlib import Path
from PIL import Image

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Folder containing images/ (and usually transforms.json)")
    ap.add_argument("--images", default="images", help="Images subfolder name")
    ap.add_argument("--masks", default="masks", help="Masks output subfolder name")
    ap.add_argument("--threshold", type=int, default=0, help="Alpha threshold: keep if alpha > threshold")
    args = ap.parse_args()

    root = Path(args.root)
    images_dir = root / args.images
    masks_dir = root / args.masks
    masks_dir.mkdir(parents=True, exist_ok=True)

    paths = sorted(images_dir.glob("*.png"))
    if not paths:
        raise SystemExit(f"No PNGs found in: {images_dir}")

    for p in paths:
        im = Image.open(p).convert("RGBA")
        alpha = im.split()[-1]
        mask = alpha.point(lambda v: 255 if v > args.threshold else 0).convert("L")
        mask.save(masks_dir / p.name)

    print(f"made {len(paths)} masks in {masks_dir}")

if __name__ == "__main__":
    main()
