from PIL import Image

from src import QOIDecoder, QOIEncoder

INPUT_IMAGE = "fruits.png"


def png_to_qoi(png_path, qoi_path):
    img = Image.open(png_path)
    width, height = img.size
    raw_data = img.tobytes()

    encoded = QOIEncoder.encode(
        raw_data,
        {
            "width": width,
            "height": height,
            "channels": len(img.getbands()),
            "colorspace": 0,
        },
    )

    with open(qoi_path, "wb") as f:
        f.write(encoded)
    print(f"Converted {png_path} to {qoi_path}")


def qoi_to_png(qoi_path, png_path):
    with open(qoi_path, "rb") as f:
        content = f.read()

    decoded = QOIDecoder.decode(content)
    mode = "RGBA" if decoded["channels"] == 4 else "RGB"

    img = Image.frombytes(
        mode, (decoded["width"], decoded["height"]), bytes(decoded["data"])
    )
    img.save(png_path)
    print(f"Converted {qoi_path} to {png_path}")


if __name__ == "__main__":
    # Example conversions
    png_to_qoi(INPUT_IMAGE, "fruits_converted.qoi")
    qoi_to_png("fruits_converted.qoi", "fruits_reconverted.png")
    assert (
        Image.open(INPUT_IMAGE).tobytes()
        == Image.open("fruits_reconverted.png").tobytes()
    ), "Reconverted image does not match original!"
