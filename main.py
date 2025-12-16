from PIL import Image

from encoder import QOIEncoder
from qoi import QOI

INPUT_IMAGE = "fruits.png"
OUTPUT_QOI = "fruits.qoi"

INPUT_IMAGE = "test.dng"
OUTPUT_QOI = "test.qoi"


def png_to_qoi(png_path, qoi_path):
    img = Image.open(png_path).convert("RGBA")
    width, height = img.size
    # Get raw bytes
    raw_data = img.tobytes()

    encoded = QOI.encode(raw_data, width, height, 4)

    with open(qoi_path, "wb") as f:
        f.write(encoded)
    print(f"Converted {png_path} to {qoi_path}")


def qoi_to_png(qoi_path, png_path):
    with open(qoi_path, "rb") as f:
        content = f.read()

    decoded = QOI.decode(content)
    mode = "RGBA" if decoded["channels"] == 4 else "RGB"

    img = Image.frombytes(
        mode, (decoded["width"], decoded["height"]), bytes(decoded["data"])
    )
    img.save(png_path)
    print(f"Converted {qoi_path} to {png_path}")


def load_image(filepath: str) -> tuple[bytes, dict]:
    """Load an image and return pixel data + description for QOI encoding."""

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

    return img.tobytes(), {
        "width": img.size[0],
        "height": img.size[1],
        "channels": channels,
        "colorspace": 0,
    }


if __name__ == "__main__":
    # Convert a sample PNG to QOI and back
    # png_to_qoi("fruits.png", "output.qoi")
    # qoi_to_png("output.qoi", "restored.png")

    pixel_data, desc = load_image(INPUT_IMAGE)
    print(
        f"Loaded image {INPUT_IMAGE}: {desc['width']}x{desc['height']} Channels: {desc['channels']}"
    )
    encoded = QOIEncoder.encode(pixel_data, desc)

    with open(OUTPUT_QOI, "wb") as f:
        f.write(encoded)
    print(f"Original image {len(pixel_data)} bytes")
    print(f"Encoded to {len(encoded)} bytes")
