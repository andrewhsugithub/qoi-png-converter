import numpy as np
from PIL import Image


def load_image(filepath: str) -> tuple[np.ndarray, dict]:
    """Load an image and return pixel data as numpy array + description."""

    ext = filepath.lower().split(".")[-1]

    if ext in ("dng", "cr2", "nef", "arw", "raw"):
        # RAW formats - requires rawpy
        import rawpy

        with rawpy.imread(filepath) as raw:
            rgb = raw.postprocess()
        img = Image.fromarray(rgb)
    else:
        # Standard formats (PNG, JPEG, etc.)
        img = Image.open(filepath)

    # Convert to RGB or RGBA
    if img.mode == "RGBA":
        channels = 4
    else:
        img = img.convert("RGB")
        channels = 3

    return np.array(img), {
        "width": img.size[0],
        "height": img.size[1],
        "channels": channels,
        "colorspace": 0,
    }
