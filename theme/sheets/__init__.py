"""The stylesheet in four parts, in the order they are applied.

base      the window, and the chrome Qt puts around it
controls  anything the operator clicks or types into
surfaces  the things content sits on: cards, bars, tabs, wells
text      headings, readouts, chips, and the state colours
"""

from theme.sheets.base import base_sheet
from theme.sheets.controls import controls_sheet
from theme.sheets.surfaces import surfaces_sheet
from theme.sheets.text import text_sheet

__all__ = ["base_sheet", "controls_sheet", "surfaces_sheet", "text_sheet"]
