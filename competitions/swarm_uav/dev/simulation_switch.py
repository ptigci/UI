"""The simulation switch in the apps' config files, written before a start.

The value is the SIMULATION box on the tab. Only the one line changes in each
file; its comments, order and line endings stay as they are.
"""

import re

from competitions.swarm_uav.config import DEVELOPER_LOCAL
from competitions.swarm_uav.dev.local_process import UI_ROOT

FIRST_MATCH_ONLY = 1


def set_simulation_mode(enabled: bool) -> None:
    """Write the switch into every file developer.toml lists.

    Raises ValueError when a file has no switch line, OSError when it cannot
    be read or written.
    """
    switch_line = DEVELOPER_LOCAL["simulation_line"].format(value=str(enabled).lower())
    for relative_path in DEVELOPER_LOCAL["simulation_files"]:
        config_path = UI_ROOT / relative_path
        # newline="" keeps the file's own line endings on the way in and out.
        with open(config_path, encoding="utf-8", newline="") as config_file:
            text = config_file.read()
        text, replaced = re.subn(
            DEVELOPER_LOCAL["simulation_pattern"], switch_line, text, FIRST_MATCH_ONLY, re.MULTILINE
        )
        if not replaced:
            raise ValueError(f"no simulation switch line in {config_path}")
        with open(config_path, "w", encoding="utf-8", newline="") as config_file:
            config_file.write(text)
