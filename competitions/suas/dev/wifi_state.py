"""Reading what nmcli says about the VTOL's wifi.

Two answers are read here: the state of its devices with its way out to the
internet, and the networks its radio can hear. nmcli's terse output is one
record per line with the fields separated by colons, and a colon inside a name
is escaped with a backslash.
"""

import re
from dataclasses import dataclass, field

from competitions.suas.config import DEVELOPER_WIFI

FIELD_SEPARATOR = DEVELOPER_WIFI["field_separator"]
# A separator that is not escaped, so an SSID with a colon in it stays whole.
UNESCAPED_SEPARATOR = re.compile(r"(?<!\\)" + re.escape(FIELD_SEPARATOR))
ESCAPED_SEPARATOR = "\\" + FIELD_SEPARATOR


def split_fields(line: str) -> list[str]:
    return [
        part.replace(ESCAPED_SEPARATOR, FIELD_SEPARATOR)
        for part in UNESCAPED_SEPARATOR.split(line)
    ]


@dataclass
class WifiState:
    """What the Pi said about its devices and its way out."""

    device_states: dict[str, str] = field(default_factory=dict)
    connectivity: str | None = None

    def wlan_state(self) -> str | None:
        return self.device_states.get(DEVELOPER_WIFI["wlan_device"])

    def wifi_connected(self) -> bool:
        return self.wlan_state() == DEVELOPER_WIFI["connected_state"]

    def has_internet(self) -> bool:
        return self.connectivity == DEVELOPER_WIFI["connectivity_full"]


def parse_connectivity(lines: list[str]) -> WifiState:
    """The device lines carry a separator; the verdict is the last line without one."""
    state = WifiState()
    for line in lines:
        if not line.strip():
            continue
        fields = split_fields(line)
        if len(fields) >= 2:
            state.device_states[fields[0]] = fields[1]
        else:
            state.connectivity = line.strip()
    return state


@dataclass(frozen=True)
class WifiNetwork:
    ssid: str
    signal_percent: int
    secured: bool


def parse_wifi_scan(lines: list[str]) -> list[WifiNetwork]:
    """The networks heard, strongest first, one entry per name, hidden ones skipped."""
    strongest: dict[str, WifiNetwork] = {}
    for line in lines:
        fields = split_fields(line)
        if len(fields) < 3 or not fields[0]:
            continue
        try:
            signal_percent = int(fields[1])
        except ValueError:
            continue
        network = WifiNetwork(fields[0], signal_percent, bool(fields[2].strip()))
        if fields[0] not in strongest or signal_percent > strongest[fields[0]].signal_percent:
            strongest[fields[0]] = network
    return sorted(strongest.values(), key=lambda network: -network.signal_percent)
