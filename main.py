from src import QOIEncoder, load_image

INPUT_IMAGE = "fruits.png"
OUTPUT_QOI = "fruits.qoi"

INPUT_IMAGE = "test.dng"
OUTPUT_QOI = "test.qoi"
OUTPUT_PNG = "test.png"

if __name__ == "__main__":
    pixel_data, desc = load_image(INPUT_IMAGE)
    print(
        f"Loaded image {INPUT_IMAGE}: {desc['width']}x{desc['height']} Channels: {desc['channels']}"
    )
    print(f"Original {INPUT_IMAGE} {len(pixel_data)} bytes")

    # Encode to QOI in pure Python (our implementation)
    encoded = QOIEncoder.encode(pixel_data.tobytes(), desc)

    with open(OUTPUT_QOI, "wb") as f:
        f.write(encoded)

    print(f"Encoded QOI to {len(encoded)} bytes")
