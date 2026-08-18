"""One folder per competition, and the switch that opens the right one.

The selection dialog decides which competition runs; everything specific to it
lives behind these start functions. Nothing outside this folder may branch on a
competition key.
"""

import logging

from competitions.international_uav import start_international_uav
from competitions.suas import start_suas
from competitions.swarm_uav import start_swarm_uav

logger = logging.getLogger(__name__)

# Competition key in config/selection.toml -> the function that opens its window.
COMPETITION_STARTERS = {
    "suru_iha": start_swarm_uav,
    "uluslararasi": start_international_uav,
    "suas": start_suas,
}


def start_competition(selection):
    """Open the main window of the selected competition, or None if unknown."""
    competition_key = selection.competition.key
    starter = COMPETITION_STARTERS.get(competition_key)
    if starter is None:
        logger.error(f"No interface is registered for competition '{competition_key}'.")
        return None
    logger.info(f"Starting the {selection.competition.label} interface.")
    return starter(selection)
