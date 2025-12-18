import struct


class QOIDecoder:
    """
    A class to decode QOI (Quite OK Image) files into raw pixel data.
    """

    @staticmethod
    def decode(
        file_data: bytes,
        byte_offset: int = 0,
        byte_length: int = None,
        output_channels: int = None,
    ) -> dict:
        """
        Decode a QOI file given as a bytes/bytearray object.

        :param file_data: Bytes containing the QOI file.
        :param byte_offset: Offset to the start of the QOI file in file_data.
        :param byte_length: Length of the QOI file in bytes.
        :param output_channels: Number of channels to include in the decoded array (3 or 4).
                                If None, uses the channels defined in the file header.
        :return: Dictionary containing width, height, colorspace, channels, and data (bytes).
        """

        # --- Handle Slicing ---
        if byte_length is None:
            byte_length = len(file_data) - byte_offset

        # Create a view of the specific slice to avoid copying large data if possible
        # or simply slice if using standard bytes
        data = file_data[byte_offset : byte_offset + byte_length]

        # --- Header Parsing ---
        # QOI Header is 14 bytes:
        # magic(4), width(4), height(4), channels(1), colorspace(1)
        if len(data) < 14:
            raise ValueError("QOI.decode: File too short for header")

        # Unpack header using struct
        # > : Big Endian
        # 4s: 4-byte string (magic)
        # I : unsigned int (4 bytes)
        # B : unsigned char (1 byte)
        magic, width, height, channels, colorspace = struct.unpack(">4sIIBB", data[:14])

        if magic != b"qoif":
            raise ValueError("QOI.decode: The signature of the QOI file is invalid")

        if output_channels is None:
            output_channels = channels

        # --- Validation ---
        if not (3 <= channels <= 4):
            raise ValueError(
                "QOI.decode: The number of channels declared in the file is invalid"
            )

        if colorspace > 1:
            raise ValueError(
                "QOI.decode: The colorspace declared in the file is invalid"
            )

        if not (3 <= output_channels <= 4):
            raise ValueError(
                "QOI.decode: The number of channels for the output is invalid"
            )

        # --- Initialization ---
        pixel_length = width * height * output_channels
        result = bytearray(pixel_length)

        # Index array: 64 pixels, initialized to (0, 0, 0, 0)
        # We store tuples for easy unpacking
        index = [(0, 0, 0, 0)] * 64

        # Initial pixel state (R, G, B, A)
        r, g, b, a = 0, 0, 0, 255

        read_pos = 14
        write_pos = 0
        run = 0
        total_pixels = width * height
        pixels_processed = 0

        # We subtract 8 to safely check for the end marker (though the loop condition below handles it via count)
        chunks_length = len(data) - 8

        # --- Decoding Loop ---
        # Iterate until we have processed all pixels
        while pixels_processed < total_pixels:

            # 1. Handle Run-Length Decoding
            if run > 0:
                run -= 1
                # We skip reading a byte and just output the current pixel again

            # 2. Read Next Op-Code (if valid)
            elif read_pos < len(data):
                b1 = data[read_pos]
                read_pos += 1

                # QOI_OP_RGB (0xFE/0b11111110)
                if b1 == 0xFE:
                    r = data[read_pos]
                    g = data[read_pos + 1]
                    b = data[read_pos + 2]
                    read_pos += 3

                # QOI_OP_RGBA (0xFF/0b11111111)
                elif b1 == 0xFF:
                    r = data[read_pos]
                    g = data[read_pos + 1]
                    b = data[read_pos + 2]
                    a = data[read_pos + 3]
                    read_pos += 4

                # QOI_OP_INDEX (00xxxxxx)
                elif (b1 & 0xC0) == 0x00:
                    r, g, b, a = index[b1]

                # QOI_OP_DIFF (01xxxxxx)
                elif (b1 & 0xC0) == 0x40:
                    # Extract 2-bit differences and subtract bias of 2
                    # Use % 256 to wrap the result to 8-bit unsigned
                    dr = ((b1 >> 4) & 0x03) - 2
                    dg = ((b1 >> 2) & 0x03) - 2
                    db = (b1 & 0x03) - 2

                    r = (r + dr) % 256
                    g = (g + dg) % 256
                    b = (b + db) % 256

                # QOI_OP_LUMA (10xxxxxx)
                elif (b1 & 0xC0) == 0x80:
                    b2 = data[read_pos]
                    read_pos += 1

                    dg = (b1 & 0x3F) - 32
                    dr_dg = ((b2 >> 4) & 0x0F) - 8
                    db_dg = (b2 & 0x0F) - 8

                    r = (r + dg + dr_dg) % 256
                    g = (g + dg) % 256
                    b = (b + dg + db_dg) % 256

                # QOI_OP_RUN (11xxxxxx)
                elif (b1 & 0xC0) == 0xC0:
                    run = b1 & 0x3F

                # 3. Update Index (Only happens if we just read a new tag)
                # The index formula: (r*3 + g*5 + b*7 + a*11) % 64
                index_pos = (r * 3 + g * 5 + b * 7 + a * 11) % 64
                index[index_pos] = (r, g, b, a)

            # 4. Write Pixel to Result
            if output_channels == 4:
                result[write_pos] = r
                result[write_pos + 1] = g
                result[write_pos + 2] = b
                result[write_pos + 3] = a
                write_pos += 4
            else:
                result[write_pos] = r
                result[write_pos + 1] = g
                result[write_pos + 2] = b
                write_pos += 3

            pixels_processed += 1

        if pixels_processed < total_pixels:
            raise ValueError("QOI.decode: Incomplete image")

        return {
            "width": width,
            "height": height,
            "colorspace": colorspace,
            "channels": output_channels,
            "data": bytes(result),
        }


# Example Usage
if __name__ == "__main__":
    # Suppose 'encoded_data' is bytes from a file.qoi
    # For testing, we can reuse the encoder from the previous step to generate data
    try:
        # Example: Create a dummy minimal valid QOI file (2x1 px, black) to test
        # Header: qoif, w=2, h=1, c=3, s=0 -> b'qoif\x00\x00\x00\x02\x00\x00\x00\x01\x03\x00'
        # Data: QOI_OP_INDEX(0) [black is at index 0 by default] -> b'\x00'
        # Run: QOI_OP_RUN(0) [run of 1] -> b'\xc0'
        # End: 00...01
        dummy_qoi = (
            b"qoif"
            + b"\x00\x00\x00\x02"  # Width 2
            + b"\x00\x00\x00\x01"  # Height 1
            + b"\x03\x00"  # Channels 3, Space 0
            + b"\x00"  # OP_INDEX (index 0 is 0,0,0,0)
            + b"\xc0"  # OP_RUN (run of 1)
            + b"\x00\x00\x00\x00\x00\x00\x00\x01"  # End marker
        )

        decoded = QOIDecoder.decode(dummy_qoi)
        print(f"Decoded: Width={decoded['width']}, Height={decoded['height']}")
        print(f"Pixel Data (Hex): {decoded['data'].hex()}")

    except Exception as e:
        print(f"Error: {e}")
