"""The simulation switch in the aircraft's config file, read and written.

The value is the SIMULATION box on the tab. Only the one line changes when it
is written; the file's comments, order and line endings stay as they are. It is
read back when the tab is built, so the box opens where the last session left
it rather than claiming the aircraft is on real hardware when its config says
otherwise.
"""

import logging
import re

from competitions.suas.config import DEVELOPER_LOCAL
from competitions.suas.dev.local_process import UI_ROOT

logger = logging.getLogger(__name__)

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


def read_simulation_mode() -> bool:
    """Whether the switch in the aircraft's config file is on.

    A file that cannot be read, or has no switch line, counts as off: the
    flight line is the safer thing to assume about a config nobody can read.
    """
    switch_line = DEVELOPER_LOCAL["simulation_line"].format(value="true")
    for relative_path in DEVELOPER_LOCAL["simulation_files"]:
        config_path = UI_ROOT / relative_path
        try:
            text = config_path.read_text(encoding="utf-8")
        except OSError as error:
            logger.warning(f"Could not read the simulation switch: {error}")
            return False
        found = re.search(DEVELOPER_LOCAL["simulation_pattern"], text, re.MULTILINE)
        if found is None or found.group().strip() != switch_line:
            return False
    return True
