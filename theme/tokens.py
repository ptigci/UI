"""Every design token as a named constant, with the derived shades mixed in.

config/theme.toml holds the values a person chooses. This module holds the ones
that follow from them — accent hover, focus ring, the tinted fill behind a
caution button — so that nothing downstream ever has to mix a colour itself.

Read tokens from here. If a widget needs a shade that is not in this file, the
shade belongs in this file.
"""

from config import THEME_TOKENS
from theme.color import blend, darken, lighten, translucent

brand = THEME_TOKENS["brand"]
surface = THEME_TOKENS["surface"]
text = THEME_TOKENS["text"]
status = THEME_TOKENS["status"]
mix = THEME_TOKENS["mix"]
font = THEME_TOKENS["font"]
space = THEME_TOKENS["space"]
radius = THEME_TOKENS["radius"]
border = THEME_TOKENS["border"]
control = THEME_TOKENS["control"]
elevation = THEME_TOKENS["elevation"]
motion = THEME_TOKENS["motion"]

# Surfaces

SURFACE_SUNKEN: str = surface["sunken"]
SURFACE_BASE: str = surface["base"]
SURFACE_CARD: str = surface["card"]
SURFACE_RAISED: str = surface["raised"]
SURFACE_OVERLAY: str = surface["overlay"]
BORDER_LINE: str = surface["line"]
BORDER_LINE_STRONG: str = surface["line_strong"]

# Text

TEXT_PRIMARY: str = text["primary"]
TEXT_SECONDARY: str = text["secondary"]
TEXT_MUTED: str = text["muted"]
# Faded from secondary rather than muted: a disabled control has to stay
# readable, and fading the dimmest text again leaves it invisible on a card.
TEXT_DISABLED: str = blend(TEXT_SECONDARY, SURFACE_BASE, mix["disabled_fade"])

# Accent, and everything mixed from it

ACCENT: str = brand["accent"]
ON_ACCENT: str = brand["on_accent"]
ACCENT_HOVER: str = lighten(ACCENT, mix["hover_lift"])
ACCENT_PRESSED: str = darken(ACCENT, mix["pressed_drop"])
FOCUS_RING: str = translucent(ACCENT, mix["focus_ring_alpha"])

# Status

STATUS_OK: str = status["ok"]
STATUS_CAUTION: str = status["caution"]
STATUS_CRITICAL: str = status["critical"]
STATUS_INFO: str = status["info"]
STATUS_IDLE: str = status["idle"]

# Text drawn on top of a filled status colour. All five are bright enough that
# the darkest surface is the readable choice, and using one keeps a caution
# button and a critical button looking like the same control.
ON_STATUS: str = SURFACE_SUNKEN

# The state vocabulary. These strings are the contract between a widget's
# dynamic property and the stylesheet, so both sides read them from here.

# No state: the element keeps the colour its role gives it. This is what a
# reading in range looks like — most of the screen, most of the time.
STATE_NONE = ""

STATE_OK = "ok"
STATE_CAUTION = "caution"
STATE_CRITICAL = "critical"
STATE_INFO = "info"
STATE_IDLE = "idle"
STATE_STALE = "stale"

STATE_COLORS: dict[str, str] = {
    STATE_OK: STATUS_OK,
    STATE_CAUTION: STATUS_CAUTION,
    STATE_CRITICAL: STATUS_CRITICAL,
    STATE_INFO: STATUS_INFO,
    STATE_IDLE: STATUS_IDLE,
    STATE_STALE: STATUS_CRITICAL,
}

# Button variants, styled once in theme/sheets/controls.py.

VARIANT_PRIMARY = "primary"
VARIANT_GHOST = "ghost"
VARIANT_CAUTION = "caution"
VARIANT_DANGER = "danger"

# Readout sizes, so a number can be large without a widget inventing a size.

SCALE_DISPLAY = "display"
SCALE_TITLE = "title"
SCALE_BODY = "body"
# Control sizes. A tile is a button big enough to be a choice in itself.
SCALE_LARGE = "large"
SCALE_TILE = "tile"
SCALE_ICON = "icon"

# What a piece of text is. Set as the `role` property — see theme/state.py.

ROLE_PAGE_TITLE = "pageTitle"
ROLE_HEADING = "heading"
ROLE_SUBHEADING = "subheading"
ROLE_READOUT = "readout"
ROLE_READOUT_LABEL = "readoutLabel"
ROLE_PILL = "pill"
ROLE_HINT = "hint"
ROLE_DIVIDER = "divider"

# What a container is. Set as the `surface` property.

AS_CARD = "card"
AS_PANEL = "panel"
AS_APP_BAR = "appBar"
AS_STRIP = "statusStrip"
AS_MAP = "map"


def soft_fill(color: str) -> str:
    """The colour tinted into a card, for a filled chip or a quiet button."""
    return blend(SURFACE_CARD, color, mix["soft_fill"])


def soft_line(color: str) -> str:
    """The border that goes with soft_fill."""
    return blend(SURFACE_CARD, color, mix["soft_line"])


# Typography

FONT_FAMILY: str = font["family"]
FONT_MONO_FAMILY: str = font["mono_family"]

FONT_SIZE_DISPLAY: int = font["size"]["display"]
FONT_SIZE_TITLE: int = font["size"]["title"]
FONT_SIZE_HEADING: int = font["size"]["heading"]
FONT_SIZE_BODY: int = font["size"]["body"]
FONT_SIZE_LABEL: int = font["size"]["label"]
FONT_SIZE_CAPTION: int = font["size"]["caption"]
FONT_SIZE_MICRO: int = font["size"]["micro"]

FONT_WEIGHT_REGULAR: int = font["weight"]["regular"]
FONT_WEIGHT_MEDIUM: int = font["weight"]["medium"]
FONT_WEIGHT_SEMIBOLD: int = font["weight"]["semibold"]
FONT_WEIGHT_BOLD: int = font["weight"]["bold"]

TRACKING_EYEBROW: float = font["tracking"]["eyebrow"]
TRACKING_DISPLAY: float = font["tracking"]["display"]

# Spacing and shape

SPACE_XS: int = space["xs"]
SPACE_SM: int = space["sm"]
SPACE_MD: int = space["md"]
SPACE_LG: int = space["lg"]
SPACE_XL: int = space["xl"]
SPACE_XXL: int = space["xxl"]

RADIUS_SM: int = radius["sm"]
RADIUS_MD: int = radius["md"]
RADIUS_LG: int = radius["lg"]
RADIUS_PILL: int = radius["pill"]

BORDER_HAIRLINE: int = border["hairline"]
BORDER_RAIL: int = border["rail"]
BORDER_FOCUS: int = border["focus"]

CONTROL_HEIGHT: int = control["height"]
CONTROL_HEIGHT_LARGE: int = control["height_large"]
TILE_WIDTH: int = control["tile_width"]
TILE_HEIGHT: int = control["tile_height"]
SCROLLBAR_WIDTH: int = control["scrollbar"]
SPIN_BUTTON_WIDTH: int = control["spin_button"]
SPIN_ARROW_SIZE: int = control["spin_arrow"]
TAB_UNDERLINE: int = control["tab_underline"]
DOT_SIZE: int = control["dot"]
DOT_HALO: int = control["dot_halo"]

# Elevation

SHADOW_ENABLED: bool = elevation["enabled"]
SHADOW_BLUR: int = elevation["blur"]
SHADOW_OFFSET_Y: int = elevation["offset_y"]
SHADOW_ALPHA: float = elevation["alpha"]
SHADOW_HOVER_BLUR: int = elevation["hover_blur"]
SHADOW_HOVER_OFFSET_Y: int = elevation["hover_offset_y"]
SHADOW_HOVER_ALPHA: float = elevation["hover_alpha"]

# Motion

DURATION_FAST: int = motion["fast"]
DURATION_BASE: int = motion["base"]
DURATION_SLOW: int = motion["slow"]
PULSE_DURATION: int = motion["pulse"]
PULSE_DEPTH: float = motion["pulse_depth"]
