"""Entry point for the ground control UI: ``cd UI && python main.py``.

Shows the competition selection dialog, then hands over to the interface of
the competition that was picked (competitions/<name>/).
"""

import logging
import sys

import colorlog
from PyQt6.QtWidgets import QApplication, QDialog

from competitions import start_competition
from config import LOG_COLORS, LOG_DATE_FORMAT, LOG_FORMAT, LOG_LEVEL
from theme import apply_theme
from windows.selection_window import SelectionWindow


def start_logging() -> None:
    """Coloured console output showing the source file and line of every message."""
    formatter = colorlog.ColoredFormatter(
        LOG_FORMAT, datefmt=LOG_DATE_FORMAT, log_colors=LOG_COLORS
    )
    handler = colorlog.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(LOG_LEVEL)


def run_selection():
    """Show the competition selection dialog; None when the user cancels."""
    selection_dialog = SelectionWindow()
    if selection_dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return selection_dialog.selection()


def main() -> None:
    start_logging()
    application = QApplication(sys.argv)
    # Every window opened after this inherits the design system.
    apply_theme(application)

    selection = run_selection()
    if selection is None:
        sys.exit(0)

    window = start_competition(selection)
    if window is None:
        sys.exit(0)

    # Opened filling the screen: the size in the form is only what it returns
    # to when the operator un-maximises it.
    window.showMaximized()
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
