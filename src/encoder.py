import struct


class QOIEncoder:
    @staticmethod
    def encode(color_data, description: dict) -> bytes:
        """
        Encode a QOI file.

        :param color_data: Bytes-like object (bytes, bytearray, list of ints) containing pixel data.
        :param description: Dictionary containing 'width', 'height', 'channels', 'colorspace'.
        :return: bytes object containing the QOI file content.
        """
        width = description.get("width")
        height = description.get("height")
        channels = description.get("channels")
        colorspace = description.get("colorspace")

        # --- Validation ---
        if not (0 <= width < 4294967296):
            raise ValueError("QOI.encode: Invalid description.width")

        if not (0 <= height < 4294967296):
            raise ValueError("QOI.encode: Invalid description.height")

        if channels not in (3, 4):
            raise ValueError("QOI.encode: Invalid description.channels, must be 3 or 4")

        if colorspace not in (0, 1):
            raise ValueError(
                "QOI.encode: Invalid description.colorspace, must be 0 or 1"
            )

        pixel_length = width * height * channels
        if len(color_data) != pixel_length:
            raise ValueError("QOI.encode: The length of colorData is incorrect")

        # --- Initialization ---
        # Result buffer (using bytearray for mutable sequence of bytes)
        # We pre-allocate a reasonable size or extend dynamically.
        # Dynamic extension is Pythonic and simpler here than managing pointers.
        result = bytearray()

        # Write Header
        # 0-3: magic "qoif"
        # 0x71 = 'q', 0x6F = 'o', 0x69 = 'i', 0x66 = 'f'
        result.extend(b"qoif")
        # 4-7: width (Big Endian), 8-11: height (Big Endian)
        # 12: channels, 13: colorspace
        result.extend(struct.pack(">IIBB", width, height, channels, colorspace))

        # Encoding State
        prev_r, prev_g, prev_b, prev_a = 0, 0, 0, 255
        run = 0

        # Index array: 64 pixels, initialized to zero.
        # Storing as tuples (r, g, b, a) for easier comparison.
        index = [(0, 0, 0, 0)] * 64

        total_pixels = width * height

        # --- Pixel Loop ---
        for i in range(0, len(color_data), channels):
            # Extract current pixel
            r = color_data[i]
            g = color_data[i + 1]
            b = color_data[i + 2]

            # Handle alpha based on channel count
            if channels == 4:
                a = color_data[i + 3]
            else:
                a = 255

            # Check for run
            if r == prev_r and g == prev_g and b == prev_b and a == prev_a:
                run += 1
                # If we hit max run length (62) or it's the very last pixel
                if run == 62 or i == (pixel_length - channels):
                    # QOI_OP_RUN
                    result.append(0b11000000 | (run - 1))
                    run = 0
            else:
                # If we were in a run, end it before processing the new pixel
                if run > 0:
                    # QOI_OP_RUN
                    result.append(0b11000000 | (run - 1))
                    run = 0

                # Check Index
                index_pos = (r * 3 + g * 5 + b * 7 + a * 11) % 64

                if index[index_pos] == (r, g, b, a):
                    result.append(index_pos)  # QOI_OP_INDEX (00xxxxxx)
                else:
                    # Update index
                    index[index_pos] = (r, g, b, a)

                    if a == prev_a:
                        # Calculate differences
                        # (x - y + 256) % 256 ensures we get the byte-wrapped difference (0-255)
                        # Then we shift range to -128..127
                        vr = (r - prev_r + 256) % 256
                        if vr > 127:
                            vr -= 256

                        vg = (g - prev_g + 256) % 256
                        if vg > 127:
                            vg -= 256

                        vb = (b - prev_b + 256) % 256
                        if vb > 127:
                            vb -= 256

                        vg_r = vr - vg
                        vg_b = vb - vg

                        # QOI_OP_DIFF
                        if (-3 < vr < 2) and (-3 < vg < 2) and (-3 < vb < 2):
                            result.append(
                                0b01000000
                                | ((vr + 2) << 4)
                                | ((vg + 2) << 2)
                                | (vb + 2)
                            )

                        # QOI_OP_LUMA
                        elif (-9 < vg_r < 8) and (-33 < vg < 32) and (-9 < vg_b < 8):
                            result.append(0b10000000 | (vg + 32))
                            result.append(((vg_r + 8) << 4) | (vg_b + 8))

                        # QOI_OP_RGB
                        else:
                            result.append(0b11111110)
                            result.extend((r, g, b))
                    else:
                        # QOI_OP_RGBA
                        result.append(0b11111111)
                        result.extend((r, g, b, a))

            prev_r, prev_g, prev_b, prev_a = r, g, b, a

        # --- End Marker ---
        # 7 bytes of 0x00 followed by 1 byte of 0x01
        result.extend(b"\x00\x00\x00\x00\x00\x00\x00\x01")

        return bytes(result)


# Example Usage
if __name__ == "__main__":
    # Create a small 2x2 test image (Red, Green, Blue, White)
    # Channels: 3 (RGB)
    width = 2
    height = 2
    channels = 3

    # Red (255,0,0), Green (0,255,0), Blue (0,0,255), White (255,255,255)
    pixel_data = [255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255]

    desc = {
        "width": width,
        "height": height,
        "channels": channels,
        "colorspace": 0,  # sRGB
    }

    try:
        encoded_qoi = QOIEncoder.encode(pixel_data, desc)
        print(f"Success! Encoded size: {len(encoded_qoi)} bytes")
        print(f"Hex output: {encoded_qoi.hex()}")
    except Exception as e:
        print(f"Error: {e}")
