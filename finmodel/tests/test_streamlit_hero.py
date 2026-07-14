from __future__ import annotations

import base64

from streamlit_app import _HERO_IMAGE_PATH, _hero_image_data_uri


def test_hero_image_is_bundled_as_a_png_data_uri() -> None:
    assert _HERO_IMAGE_PATH.is_file()

    prefix, encoded = _hero_image_data_uri().split(",", maxsplit=1)

    assert prefix == "data:image/png;base64"
    assert base64.b64decode(encoded).startswith(b"\x89PNG\r\n\x1a\n")