"""Turning what arrived on the bus into something a model can hold.

Three of these, and all three exist because the same thing is true of every
field on this bus: it was written by another machine, it crossed two radios,
and it is allowed to be missing or wrong. None of that is worth an exception on
the network thread, so a value that will not convert becomes ``None`` and a
picture that will not decode becomes no picture, and the widget above says so.

They live in their own file because both halves of the bus need them — the
mission topics in ``suas_controller.py`` and the bench topics in
``test_bus.py`` — and a helper copied into two files is a helper that will
stop agreeing with itself.
"""

import base64
import binascii


def decode_image(encoded) -> bytes:
    """Base64 to bytes, empty when it was not base64.

    Every picture on this bus arrives the same way — the detection crop, the
    preview frame, the mosaic and a slice of a file off the camera's card — and
    all of them would rather be missing than raise on the network thread.
    """
    if not encoded:
        return b""
    try:
        return base64.b64decode(encoded)
    except (binascii.Error, TypeError, ValueError):
        return b""


def int_or_none(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def float_or_none(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
