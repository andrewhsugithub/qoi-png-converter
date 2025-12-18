#! Since our QOI is in Python, and Pillow is in C, the performance difference will be significant, hence the comparison isn't entirely fair.
#! Use python's qoi (https://pypi.org/project/qoi/) package which is a C extension for a fairer comparison.

import numpy as np
from PIL import Image

import qoi as OfficialQOI
from src import load_image

INPUT_IMAGE = "fruits.png"
OUTPUT_QOI = "fruits.qoi"

INPUT_IMAGE = "test.dng"
OUTPUT_QOI = "test.qoi"
OUTPUT_PNG = "test.png"


def time_compare(pixel_data=np.ndarray):
    import time

    # Encode to QOI in pure Python (our implementation)
    start_time = time.time()
    encoded = OfficialQOI.write(OUTPUT_QOI, pixel_data)

    end_time = time.time()
    print(f"Saved QOI to {OUTPUT_QOI} in {end_time - start_time:.2f} seconds")
    print(f"Encoded QOI to {encoded} bytes")

    # Encode to PNG in C using Pillow
    start_time = time.time()

    image = Image.fromarray(pixel_data)
    image.save(OUTPUT_PNG, format="PNG")

    end_time = time.time()
    print(f"Saved PNG to {OUTPUT_PNG} in {end_time - start_time:.2f} seconds")
    print(f"Encoded PNG to {len(open(OUTPUT_PNG, 'rb').read())} bytes")


if __name__ == "__main__":
    pixel_data, desc = load_image(INPUT_IMAGE)
    print(
        f"Loaded image {INPUT_IMAGE}: {desc['width']}x{desc['height']} Channels: {desc['channels']}"
    )
    print(f"Original {INPUT_IMAGE} {pixel_data.nbytes} bytes")

    # Time Comparison Official QOI vs PNG
    time_compare(pixel_data)
