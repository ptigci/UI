"""Reading what nmcli says about the Pasifik's wifi.

Three answers are read here: the state of its devices and its way out to the
internet, the addresses it has, and the networks its radio can hear. nmcli's
terse output is one record per line with the fields separated by colons, and
a colon inside a name is escaped with a backslash.
"""

import re
from dataclasses import dataclass, field

from competitions.international_uav.config import DEVELOPER_WIFI

FIELD_SEPARATOR = DEVELOPER_WIFI["field_separator"]
SECTION_MARKER = DEVELOPER_WIFI["section_marker"]
# A separator that is not escaped, so an SSID with a colon in it stays whole.
UNESCAPED_SEPARATOR = re.compile(r"(?<!\\)" + re.escape(FIELD_SEPARATOR))
ESCAPED_SEPARATOR = "\\" + FIELD_SEPARATOR
# From ip -br addr: the interface, its state, then its addresses with prefixes.
ADDRESS_LINE = re.compile(r"^(\S+)\s+(\S+)\s+(\d+\.\d+\.\d+\.\d+)/\d+")
# The section names the wifi_state command in developer.toml announces.
CONNECTIVITY_SECTION = "connectivity"
ADDRESS_SECTION = "addr"
DEVICES_SECTION = ""


def split_fields(line: str) -> list[str]:
    return [
        part.replace(ESCAPED_SEPARATOR, FIELD_SEPARATOR)
        for part in UNESCAPED_SEPARATOR.split(line)
    ]


def split_sections(lines: list[str]) -> dict[str, list[str]]:
    """Cut one answer made of several commands back into parts by its markers.

    Whatever came before the first marker lands under the empty name.
    """
    sections: dict[str, list[str]] = {DEVICES_SECTION: []}
    current = DEVICES_SECTION
    for line in lines:
        if line.startswith(SECTION_MARKER):
            current = line[len(SECTION_MARKER):].strip()
            sections[current] = []
            continue
        sections[current].append(line)
    return sections


def parse_addresses(lines: list[str]) -> dict[str, str]:
    """Interface -> its first IPv4 address, from ip -br addr."""
    addresses = {}
    for line in lines:
        match = ADDRESS_LINE.match(line)
        if match and match.group(1) not in addresses:
            addresses[match.group(1)] = match.group(3)
    return addresses


@dataclass
class WifiState:
    """What the Pi said about its devices and its way out."""

    device_states: dict[str, str] = field(default_factory=dict)
    connectivity: str | None = None
    addresses: dict[str, str] = field(default_factory=dict)

    def wlan_state(self) -> str | None:
        return self.device_states.get(DEVELOPER_WIFI["wlan_device"])

    def ethernet_state(self) -> str | None:
        return self.device_states.get(DEVELOPER_WIFI["ethernet_device"])

    def ethernet_address(self) -> str | None:
        return self.addresses.get(DEVELOPER_WIFI["ethernet_device"])

    def wifi_connected(self) -> bool:
        return self.wlan_state() == DEVELOPER_WIFI["connected_state"]

    def has_internet(self) -> bool:
        return self.connectivity == DEVELOPER_WIFI["connectivity_full"]


def parse_wifi_state(lines: list[str]) -> WifiState:
    sections = split_sections(lines)
    state = WifiState()
    for line in sections.get(DEVICES_SECTION, []):
        fields = split_fields(line)
        if len(fields) >= 2:
            state.device_states[fields[0]] = fields[1]
    connectivity_lines = [line for line in sections.get(CONNECTIVITY_SECTION, []) if line.strip()]
    if connectivity_lines:
        state.connectivity = connectivity_lines[-1].strip()
    state.addresses = parse_addresses(sections.get(ADDRESS_SECTION, []))
    return state


@dataclass(frozen=True)
class WifiNetwork:
    ssid: str
    signal: int
    secured: bool


def parse_wifi_scan(lines: list[str]) -> list[WifiNetwork]:
    """The networks heard, strongest first, one entry per name, hidden ones skipped."""
    strongest: dict[str, WifiNetwork] = {}
    for line in lines:
        fields = split_fields(line)
        if len(fields) < 3 or not fields[0]:
            continue
        try:
            signal = int(fields[1])
        except ValueError:
            continue
        network = WifiNetwork(fields[0], signal, bool(fields[2].strip()))
        if fields[0] not in strongest or signal > strongest[fields[0]].signal:
            strongest[fields[0]] = network
    return sorted(strongest.values(), key=lambda network: -network.signal)
