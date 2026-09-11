"""Reading one line of a node's journal.

The nodes log through colorlog, so a line arrives wrapped in the escape codes
of its level's colour. A text view has no escape character to print and shows
the rest of the sequence as `[33m` rubbish across the line, so the codes come
off here and the level they stood for is handed back with the text.
"""

import re

from competitions.international_uav.config import DEVELOPER_LOG_STATES

# An SGR sequence: escape, bracket, the numbers that pick the colour, then m.
ANSI_PATTERN = re.compile(r"\x1b\[([0-9;]*)m")


def decode_log_line(line: str) -> tuple[str, str | None]:
    """The line without its escape codes, and the state its colour meant.

    Anything the nodes do not use — the reset at the end of every line, the
    background of a CRITICAL — leaves the level found so far alone.
    """
    log_state = None
    for sequence in ANSI_PATTERN.findall(line):
        for code in sequence.split(";"):
            log_state = DEVELOPER_LOG_STATES.get(code, log_state)
    return ANSI_PATTERN.sub("", line), log_state
