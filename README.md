# Setup

> See .python-version for required Python version.

1. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   # or uv
   uv venv --python 3.13
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install .
   # or uv
   uv sync
   ```

# Test images

![raw ./test.dng image](./test.dng) from https://www.signatureedits.com/free-raw-photos/

![test png image](./fruits.png)

# [QOI](https://qoiformat.org/qoi-specification.pdf) - Quite OK Image Format Overview

## File Header (14 Bytes)

The file begins with a header that defines the image dimensions and properties.

- Magic Bytes (4 bytes): The string qoif.

- Width (4 bytes): Image width in pixels (Big Endian).

- Height (4 bytes): Image height in pixels (Big Endian).

- Channels (1 byte): 3 for RGB or 4 for RGBA.

- Colorspace (1 byte): 0 for sRGB with linear alpha, or 1 for all channels linear.
  - Note: The channels and colorspace fields are informative and do not alter how the data chunks are decoded.

## Encoding State & Logic

The encoder and decoder maintain a specific state as they process pixels row by row, left to right, top to bottom.

- Starting Pixel Value: Both the encoder and decoder start with the assumption that the "previous pixel" was `r: 0, g: 0, b: 0, a: 255`.

- Index Array: A running array of 64 zero-initialized pixels is maintained. As pixels are seen, they are stored in this array at a position determined by a specific hash function: `(r * 3 + g * 5 + b * 7 + a * 11) % 64`.

## Data Chunks (Compression Operations)

Pixels are compressed into "chunks." Each chunk starts with a 2-bit or 8-bit tag. The 8-bit tags take precedence.

Here are detailed, step-by-step elaborative examples for each of the six QOI data chunks.

The QOI encoding process is essentially a decision tree for every pixel:

1. Is it a **Run** of the previous color?
2. Is it in the **Index** (seen before)?
3. Is the difference small enough for **Diff**?
4. Is the difference small enough relative to Green for **Luma**?
5. If none of the above, store the full **RGB** or **RGBA** value.

### 1. QOI_OP_RUN (Run Length Encoding)

This chunk is used when the current pixel is **identical** to the previous pixel. It is the most efficient compression method because it can represent up to 62 pixels with a single byte.

- **The Scenario:**

  - **Previous Pixel:** `(0, 0, 255, 255)` (Blue #0000FF)
  - **Upcoming Sequence:** 5 pixels of `(0, 0, 255, 255)` (Blue #0000FF)

- **Step-by-Step Encoding:**

  1. **Detect Match:** The encoder sees the pixel matches the previous one. It continues scanning and finds 4 more identical pixels. Total run length = 5.

  2. **Apply Bias:** The run length is stored with a bias of **-1**.

  $$ 5-1 = 4 $$

  3. **Form the Byte:**

     - **Tag:** `11` (binary).
     - **Payload:** `000100` (binary for 4).
     - **Combined:** `11` + `000100` = `11000100`.

- **Final Output:** `0xC4` (1 byte).

### 2. QOI_OP_INDEX (Color Indexing)

This chunk is used when the pixel color is not the same as the _immediately_ previous one, but it has been seen recently and is stored in the 64-slot running index array.

- **The Scenario:**

  - **Index Array State:** Position `29` currently holds the color `(50, 100, 50, 255)` (Dark Green).
  - **Previous Pixel:** `(255, 255, 255, 255)` (White #FFFFFF).
  - **Current Pixel:** `(50, 100, 50, 255)` (Dark Green #326432).

- **Step-by-Step Encoding:**

  1.  **Calculate Hash:** The encoder calculates the hash for the current pixel to find its index position.

      $$Index = (r \times 3 + g \times 5 + b \times 7 + a \times 11) \pmod{64}$$

      $$Index = (50 \times 3 + 100 \times 5 + 50 \times 7 + 255 \times 11) \pmod{64}$$

      $$Index = (150 + 500 + 350 + 2805) \pmod{64}$$

      $$Index = 3805 \pmod{64} = 29$$

      _(Note: In this specific scenario, let's assume the hash collision logic or previous history placed our specific Dark Green color at index **29** for the sake of the example)._

  2.  **Check Index:** The encoder checks `Index[29]`. It matches the current pixel.

  3.  **Form the Byte:**

      - **Tag:** `00` (binary).

      - **Payload:** `011101` (binary for index 29).
      - **Combined:** `00` + `011101` = `00011101`.

- **Final Output:** `0x1D` (1 byte).

### 3. QOI_OP_DIFF (Small Differences)

This chunk is used for slight color variations (e.g., gradients or noise). It encodes the **difference** between the current and previous pixel for R, G, and B. It only works if the difference is very small (between -2 and +1). Alpha must remain unchanged.

- **The Scenario:**

  - **Previous Pixel:** `(100, 100, 100, 255)` (Gray #646464)
  - **Current Pixel:** `(101, 99, 100, 255)` (Slightly Reddish Gray #656364)

- **Step-by-Step Encoding:**

  1. **Calculate Diffs:**

     - $dr = 101 - 100 = +1$
     - $dg = 99 - 100 = -1$
     - $db = 100 - 100 = 0$

  2. **Apply Bias:** Add a bias of **2** to make the numbers unsigned.

     - $dr = 1 + 2 = 3$ (binary `11`)
     - $dg = -1 + 2 = 1$ (binary `01`)
     - $db = 0 + 2 = 2$ (binary `10`)

  3. **Form the Byte:**

     - **Tag:** `01` (binary).

     - **Payload:** Sequence of `dr`, `dg`, `db`.
     - **Combined:** `01` | `11` | `01` | `10` = `01110110`.

- **Final Output:** `0x76` (1 byte).

### 4. QOI_OP_LUMA (Luminance/Green Difference)

This chunk handles larger color shifts than `OP_DIFF`. It relies on the fact that the Green channel usually changes similarly to Red and Blue. It uses the Green difference as a baseline reference.

- **The Scenario:**

  - **Previous Pixel:** `(100, 100, 100, 255)` (Gray #646464)
  - **Current Pixel:** `(120, 125, 122, 255)` (Significantly brighter #78797A)
  - _Note:_ The changes (+20, +25, +22) are too big for `OP_DIFF`.

- **Step-by-Step Encoding:**

  1. **Calculate Green Diff (`dg`):**
     $$dg = 125 - 100 = +25$$
     (Range allowed: -32..31) .

  2. **Calculate Dr_Dg and Db_Dg:** These are the differences of Red and Blue _minus_ the Green difference.

     - $dr\\_dg = (120 - 100) - 25 = 20 - 25 = -5$
     - $db\\_dg = (122 - 100) - 25 = 22 - 25 = -3$
       (Range allowed: -8..7) .

  3. **Apply Biases:**

     - Green Bias (+32): $25 + 32 = 57$ (binary `111001`).

     - Dr_Dg Bias (+8): $-5 + 8 = 3$ (binary `0011`).

     - Db_Dg Bias (+8): $-3 + 8 = 5$ (binary `0101`).

  4. **Form the Bytes:**

     - **Byte 1 (Tag + Green):** Tag `10` + `111001` = `10111001` (`0xB9`).
     - **Byte 2 (Dr + Db):** `0011` (high nibble) | `0101` (low nibble) = `00110101` (`0x35`).

- **Final Output:** `0xB9 0x35` (2 bytes).

### 5. QOI_OP_RGB (Full RGB)

This is the fallback when the color change is too large for Diff/Luma and not in the Index, but the **Alpha** channel is unchanged.

- **The Scenario:**

  - **Previous Pixel:** `(0, 0, 0, 255)` (Black #000000)
  - **Current Pixel:** `(255, 0, 128, 255)` (Bright Pink #FF0080)
  - _Analysis:_ The difference is huge (+255). No relationship between channels.

- **Step-by-Step Encoding:**

  1.  **Identify Chunk:** Use `QOI_OP_RGB` because Alpha is still 255.
  2.  **Form the Bytes:**

      - **Byte 0 (Tag):** `11111110` (`0xFE`).

      - **Byte 1 (Red):** `255` (`0xFF`).

      - **Byte 2 (Green):** `0` (`0x00`).

      - **Byte 3 (Blue):** `128` (`0x80`).

- **Final Output:** `0xFE FF 00 80` (4 bytes).

### 6. QOI_OP_RGBA (Full RGBA)

This is the ultimate fallback when even the **Alpha** channel has changed.

- **The Scenario:**

  - **Previous Pixel:** `(255, 0, 128, 255)` (Opaque Pink #FF0080)
  - **Current Pixel:** `(100, 100, 100, 128)` (Semi-transparent Gray #64646480)

- **Step-by-Step Encoding:**

  1. **Identify Chunk:** Alpha changed from 255 to 128. Must use `QOI_OP_RGBA`.
  2. **Form the Bytes:**

     - **Byte 0 (Tag):** `11111111` (`0xFF`).

     - **Byte 1 (Red):** `100` (`0x64`).

     - **Byte 2 (Green):** `100` (`0x64`).

     - **Byte 3 (Blue):** `100` (`0x64`).

     - **Byte 4 (Alpha):** `128` (`0x80`).

- **Final Output:** `0xFF 64 64 64 80` (5 bytes).

## End Marker

The end of the QOI stream is explicitly marked by a sequence of 8 bytes: seven 0x00 bytes followed by a single 0x01 byte.
