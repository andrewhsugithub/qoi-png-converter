import numpy as np

import qoi as OfficialQOI
from src import QOIDecoder, QOIEncoder, load_image

INPUT_IMAGE = "fruits.png"
INPUT_IMAGE = "test.dng"


def test_qoi():
    """Verify that our QOI implementation is correct by round-tripping."""
    pixel_data, desc = load_image(INPUT_IMAGE)

    # Encode to QOI
    encoded = OfficialQOI.encode(pixel_data)
    our_encoded = QOIEncoder.encode(pixel_data.tobytes(), desc)
    assert encoded == our_encoded, "Encoded data mismatch!"

    # Decode back
    decoded = OfficialQOI.decode(encoded)
    our_decoded = QOIDecoder.decode(our_encoded)
    our_decoded_array = np.frombuffer(our_decoded["data"], dtype=np.uint8).reshape(
        desc["height"], desc["width"], desc["channels"]
    )
    assert np.array_equal(decoded, our_decoded_array), "Decoded data mismatch!"
