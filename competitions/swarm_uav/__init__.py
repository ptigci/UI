"""Sürü İHA interface: swarm tab plus one tab per drone and VTOL."""

from competitions.swarm_uav.windows.main_window import MainWindow


def start_swarm_uav(selection):
    """Open the Sürü İHA main window for the selected vehicle counts."""
    return MainWindow(selection)
