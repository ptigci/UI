"""Entry point for the ground control UI: ``cd UI && python main.py``.

Shows the competition selection dialog, then hands over to the interface of
the competition that was picked (competitions/<name>/).
"""

import argparse
import logging
import sys

import colorlog
from PyQt6.QtWidgets import QApplication, QDialog

from competitions import start_competition
from config import (
    COMPETITIONS,
    DEVELOPER_MODE_DEFAULT,
    DRONE_COUNT_DEFAULT,
    LOG_COLORS,
    LOG_DATE_FORMAT,
    LOG_FORMAT,
    LOG_LEVEL,
    VTOL_COUNT_DEFAULT,
)
from theme import apply_theme
from windows.selection_window import SelectionResult, SelectionWindow


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


def selection_from_arguments(arguments):
    """A selection made on the command line, so a launch skips the dialog.

    ``--competition <key>`` picks the competition by its key in
    config/selection.toml, with the default vehicle counts and developer
    mode on or off with ``--developer`` / ``--no-developer``. Nothing given
    means the dialog as before. A competition clock that starts on power-up
    is the reason this exists.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--competition", default=None)
    parser.add_argument("--developer", dest="developer", action="store_true",
                        default=None)
    parser.add_argument("--no-developer", dest="developer", action="store_false")
    options, unused = parser.parse_known_args(arguments)
    if options.competition is None:
        return None

    for competition in COMPETITIONS:
        if competition.key == options.competition:
            developer_mode = DEVELOPER_MODE_DEFAULT
            if options.developer is not None:
                developer_mode = options.developer
            developer_mode = developer_mode and competition.supports_developer_mode
            return SelectionResult(competition, DRONE_COUNT_DEFAULT,
                                   VTOL_COUNT_DEFAULT, developer_mode)

    logging.getLogger(__name__).error(
        f"No competition is called '{options.competition}'; showing the dialog."
    )
    return None


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

    selection = selection_from_arguments(sys.argv[1:])
    if selection is None:
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
