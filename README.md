Pure Python implementation of the [Quite OK Image (QOI)](https://qoiformat.org/qoi-specification.pdf) format, which is a fast, lossless image compression format designed for simplicity and speed.

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

# Encode an image to QOI with our implementation

> Note: Change `INPUT_IMAGE` in `main.py` to test with different images. Same for `OUTPUT_*` variables.

```bash
python main.py
# or uv
uv run main.py
```

# Convert PNG to QOI or QOI to PNG using our QOI implementation

```bash
python converter.py
# or uv
uv run converter.py
```

> Note: Change the `INPUT_IMAGE` variable in `converter.py` to test with different images.

# Test images

![raw ./test.dng image](./test.dng) from https://www.signatureedits.com/free-raw-photos/

![test png image](./fruits.png)

# Comparison with PNG

We can compare the QOI encoded file size and encoding time with PNG for the same image (`./test.dng`).

```bash
uv run comparison.py
```

> Note: PNG encoding is done using Pillow which is implemented in C, while our QOI implementation is in pure Python. Hence the performance difference will be significant, and the comparison isn't entirely fair. For a fairer comparison, we used a C extension Python wrapper for [QOI](https://github.com/kodonnell/qoi) comparison.

## Results

```bash
Loaded image test.dng: 5784x8672 Channels: 3
Original test.dng 150476544 bytes
Saved QOI to test.qoi in 0.28 seconds
Encoded QOI to 76246966 bytes
Saved PNG to test.png in 2.36 seconds
Encoded PNG to 63311468 bytes
```

The QOI encoded file is about 50% the size of the original raw image, while PNG is about 42% since PNG uses more complex compression, see detailed comparison below. However, QOI encoding is significantly faster than PNG encoding. This demonstrates QOI's efficiency in both speed and compression for lossless image formats.

# Our QOI Implementation vs [QOI C Extension](https://github.com/kodonnell/qoi)

Test correctness to ensure our implementation matches the output of the C extension.

```bash
pytest .
```

# PNG vs QOI Detailed Comparison

### Overview

| Feature              | PNG (Portable Network Graphics)                                                    | QOI (Quite OK Image)                                                       |
| -------------------- | ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **Compression Type** | **Lossless** (primary). Can be lossy via pre-processing (quantization).            | **Strictly Lossless**. No lossy mode exists in the spec.                   |
| **Color Spaces**     | **Versatile**. Supports Grayscale, Indexed (Palette), RGB, and RGBA.               | **Limited**. Supports only **RGB** (3 channels) and **RGBA** (4 channels). |
| **Bit Depth**        | **Flexible**. 1, 2, 4, 8, or **16 bits** per channel.                              | **Fixed**. Strictly **8 bits** per channel (24-bit RGB or 32-bit RGBA).    |
| **Transparency**     | **Full Alpha Channel** (8/16-bit) or simple binary transparency (tRNS chunk).      | **Full Alpha Channel** (8-bit) only.                                       |
| **Animation**        | **Not Native**. Requires APNG extension (widely supported but separate).           | **No**. Single frame static images only.                                   |
| **Streaming**        | **Difficult**. Requires complex buffering to handle chunk logic and Huffman trees. | **Excellent**. Designed for O(n) streaming with minimal RAM.               |
| **Interlacing**      | **Supported** (Adam7). Allows blurry preview while downloading.                    | **No**. Encodes strictly row-by-row, top-to-bottom.                        |
| **Endianness**       | **Big Endian** (Network Byte Order).                                               | **Big Endian**. Matches PNG convention.                                    |
| **Metadata**         | **Rich**. EXIF, ICC Profiles, Gamma, Text, Last Modified Time.                     | **Minimal**. Only flags for sRGB vs. Linear color space.                   |

### Compression Pipeline

**Comparison of the step-by-step workflow from raw pixels to file output.**

| Step                    | PNG (Deflate Algorithm)                                                                                                               | QOI (Quite OK Image Algorithm)                                                                                     |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **1. Pre-processing**   | **Filtering:** Applies one of 5 filters (None, Sub, Up, Average, Paeth) to every scanline to predict pixel values based on neighbors. | **None:** Reads raw pixels directly (R, G, B, A) in a single pass.                                                 |
| **2. Pattern Matching** | **LZ77 Sliding Window:** Searches a 32KB history window to find repeating sequences of bytes (strings of data).                       | **Streaming Decision:** Checks only the _immediately previous pixel_ or a _64-slot cache_ of recently seen colors. |
| **3. Entropy Coding**   | **Huffman Coding:** Converts symbols into variable-length bit codes (e.g., frequent values get 3 bits, rare get 10 bits).             | **None:** Writes fixed-size chunks (chunks are always aligned to whole bytes).                                     |
| **4. Output Format**    | **Bit-Stream:** A continuous stream of bits; data boundaries do not align with byte boundaries.                                       | **Byte-Stream:** A stream of 8-bit bytes; no bit-shifting required to read/write.                                  |

### Memory & Lookback "Context"

**How much historical data the encoder must maintain to make decisions.**

| Feature              | PNG                                                                                                       | QOI                                                                                                       |
| -------------------- | --------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **Lookback Scope**   | **32 KB Window:** Can reference a pixel pattern seen thousands of pixels ago.                             | **Last Pixel + 64 Cache:** Can only reference the very last pixel or one of 64 recent distinct colors.    |
| **Search Cost**      | **High (Linear/Tree):** The encoder must search the 32KB window to find the "longest match."              | **Instant (O(1)):** Uses a simple hash: `(r*3 + g*5 + b*7 + a*11) % 64` to jump directly to a cache slot. |
| **Prediction Logic** | **Complex 2D:** The "Paeth" filter looks at Left, Up, and Upper-Left pixels to predict the current value. | **Simple 1D:** Only looks at the previous pixel (Left) to calculate differences.                          |

### Computational Complexity (CPU Operations)

**Why QOI executes faster on modern hardware.**

| Complexity Factor   | PNG                                                                                           | QOI                                                                                   |
| ------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **Data Alignment**  | **Bit-Packing:** CPU must perform extensive bit-shifting and masking to decode Huffman trees. | **Byte-Aligned:** CPU loads full 8-bit, 16-bit, or 32-bit words directly from memory. |
| **Math Operations** | **Heavy:** Requires absolute differences, linear functions (Paeth), and tree traversals.      | **Light:** Uses simple integer addition/subtraction and equality checks (`==`).       |
| **Branching**       | **Predictable but Deep:** Deep loop structures for Huffman decoding.                          | **Shallow:** simple `if/else` ladder (Is it a run? Is it in cache? Is it a diff?).    |
| **Time Complexity** | **Variable:** Depends heavily on "effort" settings (how hard to search the LZ77 window).      | **O(n):** Linear time. Touches every pixel exactly once.                              |

### Encoding Operations (Opcodes)

**How specific pixel scenarios are written to the file.**

| Scenario             | PNG (Deflate Stream)                                                                                    | QOI (Explicit Opcode)                                                                              |
| -------------------- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Repeating Pixels** | **Length/Distance Pair:** A code saying "Go back X bytes and copy Y bytes."                             | **`QOI_OP_RUN`:** A 1-byte tag saying "Repeat previous pixel X times" (max 62).                    |
| **Recent Color**     | **LZ77 Match:** References the position in the sliding window where this color last appeared.           | **`QOI_OP_INDEX`:** A 1-byte tag pointing to index 0-63 in the color array.                        |
| **Small Change**     | **Filter + Huffman:** Filter reduces value to small integer \to Huffman encodes it.                     | **`QOI_OP_DIFF`:** A 1-byte tag storing the 2-bit difference for R, G, and B.                      |
| **Luminance Change** | **N/A:** Handled generally by filters.                                                                  | **`QOI_OP_LUMA`:** A 2-byte sequence optimizing for green channel changes (human eye sensitivity). |
| **New Unique Color** | **Literal Byte:** Writes the raw byte, potentially expanding file size if Huffman tree isn't optimized. | **`QOI_OP_RGB`:** A 4-byte tag writing the full raw Red, Green, Blue values immediately.           |

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
