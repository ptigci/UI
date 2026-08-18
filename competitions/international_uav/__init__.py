"""Uluslararası İHA interface: Pasifik scans, the operator confirms, the swarm flies."""

from competitions.international_uav.windows import InternationalMainWindow


def start_international_uav(selection):
    """Open the Uluslararası İHA operations window for the selected swarm size."""
    return InternationalMainWindow(selection)
