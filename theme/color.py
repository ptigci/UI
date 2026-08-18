"""Colour arithmetic, so the palette can be derived from a handful of values.

Every hover, pressed, tinted and disabled shade in the interface is mixed here
at load time. That is what makes config/theme.toml a real brand switch: change
the accent and the forty shades that hang off it follow.

Mixing produces opaque hex rather than a translucent overlay on purpose. Qt
composites a translucent stylesheet colour against whatever the widget happens
to be sitting on, which is exactly how a design system drifts.
"""

WHITE = "#FFFFFF"
BLACK = "#000000"

HEX_DIGITS_PER_CHANNEL = 2
CHANNEL_MAX = 255


def parse_color(color: str) -> tuple[int, int, int]:
    """'#RRGGBB' to its three channels."""
    digits = color.lstrip("#")
    return tuple(
        int(digits[position : position + HEX_DIGITS_PER_CHANNEL], 16)
        for position in range(0, len(digits), HEX_DIGITS_PER_CHANNEL)
    )


def format_color(channels: tuple[int, int, int]) -> str:
    red, green, blue = channels
    return f"#{red:02X}{green:02X}{blue:02X}"


def blend(base_color: str, mixed_color: str, amount: float) -> str:
    """Pull base_color the given fraction of the way towards mixed_color."""
    base_channels = parse_color(base_color)
    mixed_channels = parse_color(mixed_color)
    return format_color(
        tuple(
            round(base + (mixed - base) * amount)
            for base, mixed in zip(base_channels, mixed_channels)
        )
    )


def lighten(color: str, amount: float) -> str:
    return blend(color, WHITE, amount)


def darken(color: str, amount: float) -> str:
    return blend(color, BLACK, amount)


def translucent(color: str, alpha: float) -> str:
    """A Qt rgba() string. Only for rings and shadows, never for a fill."""
    red, green, blue = parse_color(color)
    return f"rgba({red}, {green}, {blue}, {round(alpha * CHANNEL_MAX)})"
