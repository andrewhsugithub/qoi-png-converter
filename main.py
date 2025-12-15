from qoi import QOI

# # Create a dummy 2x2 gradient image (RGBA)
# # Red, Green
# # Blue, White
# width = 2
# height = 2
# channels = 4
# raw_pixels = bytearray([
#     255, 0, 0, 255,   0, 255, 0, 255,
#     0, 0, 255, 255,   255, 255, 255, 255
# ])

# # ENCODE
# encoded_qoi = QOI.encode(raw_pixels, width, height, channels)
# with open("test.qoi", "wb") as f:
#     f.write(encoded_qoi)
# print("Encoded test.qoi")

# # DECODE
# with open("test.qoi", "rb") as f:
#     data = f.read()
    
# decoded = QOI.decode(data)
# print(f"Decoded Size: {decoded['width']}x{decoded['height']}")
# print(f"Decoded Pixels match: {decoded['data'] == raw_pixels}")

from PIL import Image

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
    mode = "RGBA" if decoded['channels'] == 4 else "RGB"
    
    img = Image.frombytes(mode, (decoded['width'], decoded['height']), bytes(decoded['data']))
    img.save(png_path)
    print(f"Converted {qoi_path} to {png_path}")

# Example Usage:
# png_to_qoi("fruits.png", "output.qoi")
qoi_to_png("output.qoi", "restored.png")