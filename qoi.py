import struct

class QOI:
    # QOI Constants
    QOI_OP_INDEX = 0x00
    QOI_OP_DIFF  = 0x40
    QOI_OP_LUMA  = 0x80
    QOI_OP_RUN   = 0xC0
    QOI_OP_RGB   = 0xFE
    QOI_OP_RGBA  = 0xFF

    QOI_MASK_2   = 0xC0
    QOI_HEADER_SIZE = 14
    QOI_MAGIC = b'qoif'
    QOI_PIXELS_MAX = 400000000  # Safety limit (400MP)

    @staticmethod
    def _hash(r, g, b, a):
        """Calculates the index position for the color array."""
        return (r * 3 + g * 5 + b * 7 + a * 11) % 64

    @classmethod
    def encode(cls, raw_bytes, width, height, channels, colorspace=0):
        """
        Encodes raw pixel data into QOI format.
        :param raw_bytes: bytes or bytearray of pixel data (RGB or RGBA)
        :param width: image width
        :param height: image height
        :param channels: 3 (RGB) or 4 (RGBA)
        :param colorspace: 0 (sRGB) or 1 (Linear)
        :return: bytearray of encoded QOI data
        """
        if len(raw_bytes) != width * height * channels:
            raise ValueError("Raw byte length does not match image dimensions.")

        # Initialize Output
        out = bytearray()
        
        # 1. Write Header
        # Magic(4), Width(4), Height(4), Channels(1), Colorspace(1)
        out.extend(cls.QOI_MAGIC)
        out.extend(struct.pack(">IIBB", width, height, channels, colorspace))

        # State Variables
        index = [[0, 0, 0, 0]] * 64 # Color lookup table (zero initialized)
        px_prev = (0, 0, 0, 255)    # r, g, b, a (defaults to opaque black)
        run = 0
        total_pixels = width * height
        
        # Iterate over pixels
        # We step through the raw_bytes based on channel count
        for i in range(0, len(raw_bytes), channels):
            # Extract current pixel components
            r = raw_bytes[i]
            g = raw_bytes[i+1]
            b = raw_bytes[i+2]
            a = raw_bytes[i+3] if channels == 4 else 255
            px_curr = (r, g, b, a)

            # Check for Run match
            if px_curr == px_prev:
                run += 1
                if run == 62 or (i + channels) == len(raw_bytes):
                    # Write QOI_OP_RUN
                    out.append(cls.QOI_OP_RUN | (run - 1))
                    run = 0
                continue
            
            # If we had a run that ended, write it now
            if run > 0:
                out.append(cls.QOI_OP_RUN | (run - 1))
                run = 0

            # Check Index
            idx_pos = cls._hash(r, g, b, a)
            if index[idx_pos] == list(px_curr):
                out.append(cls.QOI_OP_INDEX | idx_pos)
                px_prev = px_curr
                continue

            # Save current pixel to index
            index[idx_pos] = list(px_curr)

            # Check Diff (RGB only, alpha must match prev)
            if a == px_prev[3]:
                vr = (r - px_prev[0]) & 0xFF
                vg = (g - px_prev[1]) & 0xFF
                vb = (b - px_prev[2]) & 0xFF

                # Convert to signed 8-bit for comparison
                d_r = (vr - 256) if vr > 127 else vr
                d_g = (vg - 256) if vg > 127 else vg
                d_b = (vb - 256) if vb > 127 else vb

                # QOI_OP_DIFF (2-bit diffs)
                if -2 <= d_r <= 1 and -2 <= d_g <= 1 and -2 <= d_b <= 1:
                    out.append(
                        cls.QOI_OP_DIFF | 
                        ((d_r + 2) << 4) | 
                        ((d_g + 2) << 2) | 
                        (d_b + 2)
                    )
                    px_prev = px_curr
                    continue

                # QOI_OP_LUMA (Green diff, and dr-dg, db-dg)
                dr_dg = (d_r - d_g)
                db_dg = (d_b - d_g)
                if -32 <= d_g <= 31 and -8 <= dr_dg <= 7 and -8 <= db_dg <= 7:
                    out.append(cls.QOI_OP_LUMA | (d_g + 32))
                    out.append(((dr_dg + 8) << 4) | (db_dg + 8))
                    px_prev = px_curr
                    continue

            # Fallback: QOI_OP_RGB or QOI_OP_RGBA
            if a == px_prev[3]:
                # RGB
                out.append(cls.QOI_OP_RGB)
                out.extend((r, g, b))
            else:
                # RGBA
                out.append(cls.QOI_OP_RGBA)
                out.extend((r, g, b, a))

            px_prev = px_curr

        # End Marker (7 bytes 0x00, 1 byte 0x01)
        out.extend(b'\x00' * 7 + b'\x01')
        return out

    @classmethod
    def decode(cls, qoi_data):
        """
        Decodes QOI data into raw pixels.
        :param qoi_data: bytes of the .qoi file
        :return: dictionary {width, height, channels, colorspace, bytes}
        """
        # Read Header
        if qoi_data[:4] != cls.QOI_MAGIC:
            raise ValueError("Invalid Magic Bytes")
        
        width, height, channels, colorspace = struct.unpack(">IIBB", qoi_data[4:14])
        
        total_pixels = width * height
        pixel_data = bytearray(total_pixels * channels)
        
        # State
        index = [[0, 0, 0, 0]] * 64
        r, g, b, a = 0, 0, 0, 255
        
        p = 14 # Pointer to data
        data_len = len(qoi_data) - 8 # Ignore end marker for loop safety
        pixel_pos = 0

        while pixel_pos < len(pixel_data) and p < data_len:
            byte1 = qoi_data[p]
            p += 1

            if byte1 == cls.QOI_OP_RGB:
                r, g, b = qoi_data[p], qoi_data[p+1], qoi_data[p+2]
                p += 3
            
            elif byte1 == cls.QOI_OP_RGBA:
                r, g, b, a = qoi_data[p], qoi_data[p+1], qoi_data[p+2], qoi_data[p+3]
                p += 4
            
            elif (byte1 & cls.QOI_MASK_2) == cls.QOI_OP_INDEX:
                idx = byte1 & 0x3F
                r, g, b, a = index[idx]
            
            elif (byte1 & cls.QOI_MASK_2) == cls.QOI_OP_DIFF:
                r = (r + ((byte1 >> 4) & 0x03) - 2) & 0xFF
                g = (g + ((byte1 >> 2) & 0x03) - 2) & 0xFF
                b = (b + (byte1 & 0x03) - 2) & 0xFF
            
            elif (byte1 & cls.QOI_MASK_2) == cls.QOI_OP_LUMA:
                byte2 = qoi_data[p]
                p += 1
                dg = (byte1 & 0x3F) - 32
                r = (r + dg - 8 + ((byte2 >> 4) & 0x0F)) & 0xFF
                g = (g + dg) & 0xFF
                b = (b + dg - 8 + (byte2 & 0x0F)) & 0xFF

            elif (byte1 & cls.QOI_MASK_2) == cls.QOI_OP_RUN:
                run = (byte1 & 0x3F)
                # Emit the current pixel run+1 times
                # We do this logic slightly differently for decode
                # to handle the loop cleanly
                for _ in range(run + 1):
                    pixel_data[pixel_pos]   = r
                    pixel_data[pixel_pos+1] = g
                    pixel_data[pixel_pos+2] = b
                    if channels == 4:
                        pixel_data[pixel_pos+3] = a
                    pixel_pos += channels
                continue # Skip the single append at the bottom

            # Update Index
            idx_pos = cls._hash(r, g, b, a)
            index[idx_pos] = [r, g, b, a]

            # Append Pixel
            pixel_data[pixel_pos]   = r
            pixel_data[pixel_pos+1] = g
            pixel_data[pixel_pos+2] = b
            if channels == 4:
                pixel_data[pixel_pos+3] = a
            pixel_pos += channels

        return {
            'width': width,
            'height': height,
            'channels': channels,
            'colorspace': colorspace,
            'data': pixel_data
        }