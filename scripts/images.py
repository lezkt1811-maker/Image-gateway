#!/usr/bin/env python3
"""Instagram image helper: check a folder, or pad an image to 4:5.

    python scripts/images.py check <folder>        # exit 1 if any image is unusable
    python scripts/images.py pad <src> <dst.jpg>   # add dark bars so the ratio is 4:5

Instagram accepts JPEG at a width of 320 px or more, with an aspect ratio between
4:5 (0.8) and 1.91:1. Anything outside that is rejected by the API.
"""
import sys
from pathlib import Path

from PIL import Image, ImageOps

MIN_RATIO, MAX_RATIO = 0.8, 1.91
MIN_WIDTH = 320
BACKGROUND = (11, 8, 22)  # the dark space colour used on the site
EXTENSIONS = {".jpg", ".jpeg", ".png"}


def check(folder):
    problems = 0
    files = sorted(p for p in Path(folder).rglob("*") if p.suffix.lower() in EXTENSIONS)
    if not files:
        print(f"no images found in {folder}")
        return 1
    for path in files:
        with Image.open(path) as img:
            w, h = ImageOps.exif_transpose(img).size
        ratio = w / h
        issues = []
        if w < MIN_WIDTH:
            issues.append(f"width {w}px is below {MIN_WIDTH}px")
        if not MIN_RATIO <= ratio <= MAX_RATIO:
            issues.append(f"ratio {ratio:.3f} is outside {MIN_RATIO}-{MAX_RATIO} (run 'pad')")
        if " " in path.name:
            issues.append("file name has spaces (use hyphens)")
        status = "FAIL" if any("ratio" in i or "width" in i for i in issues) else "ok  "
        print(f"{status} {path} {w}x{h} ({ratio:.3f})" + (" - " + "; ".join(issues) if issues else ""))
        problems += status == "FAIL"
    print(f"images: {len(files)} checked, {problems} unusable for Instagram")
    return 1 if problems else 0


def pad(src, dst):
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
    w, h = img.size
    ratio = w / h
    if MIN_RATIO <= ratio <= MAX_RATIO:
        canvas = img
    elif ratio < MIN_RATIO:  # too tall: add bars top and bottom
        new_h = round(w / MIN_RATIO)
        canvas = Image.new("RGB", (w, new_h), BACKGROUND)
        canvas.paste(img, (0, (new_h - h) // 2))
    else:  # too wide: add bars left and right
        new_w = round(h * MAX_RATIO)
        canvas = Image.new("RGB", (new_w, h), BACKGROUND)
        canvas.paste(img, ((new_w - w) // 2, 0))
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dst, "JPEG", quality=92, optimize=True, progressive=True)
    print(f"wrote {dst} {canvas.size[0]}x{canvas.size[1]}")
    return 0


def main(argv):
    if len(argv) == 3 and argv[1] == "check":
        return check(argv[2])
    if len(argv) == 4 and argv[1] == "pad":
        return pad(argv[2], argv[3])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
