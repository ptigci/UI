"""What the ping test found, and how each answer is read.

Two sides answer: this laptop, one process per question, and the VTOL's Pi,
one ssh call whose answer is cut back into parts by marker lines. The report
is plain data — the network table draws it and the diagnosis reads it. A ping
is an average in milliseconds, or None when nothing came back.
"""

import re
import statistics
from dataclasses import dataclass, field

from competitions.suas.config import DEVELOPER_NETWORK

IPV4_ADDRESS = re.compile(r"(\d+\.\d+\.\d+\.\d+)")
# From ip -br addr: the interface, its state, then its addresses with prefixes.
ADDRESS_LINE = re.compile(r"^(\S+)\s+(\S+)\s+(\d+\.\d+\.\d+\.\d+)/\d+")
# ip neigh names a neighbour it has a hardware address for with this.
NEIGHBOUR_KNOWN_MARK = "lladdr"
NEIGHBOUR_FAILED_MARK = "FAILED"
# A reply that came back without a time the pattern could read.
UNKNOWN_AVERAGE_MS = 0.0

SECTION_PREFIX = DEVELOPER_NETWORK["section_prefix"]
NEIGHBOURS_SECTION = DEVELOPER_NETWORK["neighbours_section"]
PING_SECTION = DEVELOPER_NETWORK["ping_section"]
SOCKET_SECTION = DEVELOPER_NETWORK["socket_section"]
ADDRESSES_SECTION = ""
KNOWN_SECTIONS = (NEIGHBOURS_SECTION, PING_SECTION, SOCKET_SECTION)
PING_HOST_PREFIX = DEVELOPER_NETWORK["ping_host_prefix"]


def parse_gcs_ping(lines: list[str]) -> float | None:
    """Windows ping: count the replies and average the times they carry."""
    replies = 0
    times = []
    time_regex = re.compile(DEVELOPER_NETWORK["gcs_time_pattern"])
    for line in lines:
        if DEVELOPER_NETWORK["gcs_reply_pattern"].lower() in line.lower():
            replies += 1
        match = time_regex.search(line)
        if match:
            times.append(float(match.group(1)))
    if replies == 0:
        return None
    if not times:
        return UNKNOWN_AVERAGE_MS
    return statistics.fmean(times)


def parse_pi_ping(lines: list[str]) -> float | None:
    """Linux ping's last two lines: the count received and the min/avg/max."""
    received = 0
    average_ms = None
    for line in lines:
        received_match = re.search(DEVELOPER_NETWORK["pi_received_pattern"], line)
        if received_match:
            received = int(received_match.group(1))
        average_match = re.search(DEVELOPER_NETWORK["pi_average_pattern"], line)
        if average_match:
            average_ms = float(average_match.group(1))
    if received == 0:
        return None
    if average_ms is None:
        return UNKNOWN_AVERAGE_MS
    return average_ms


def parse_ipconfig(lines: list[str]) -> list[str]:
    addresses = []
    for line in lines:
        if DEVELOPER_NETWORK["gcs_address_line_mark"] not in line:
            continue
        match = IPV4_ADDRESS.search(line)
        if match:
            addresses.append(match.group(1))
    return addresses


def parse_arp(lines: list[str], prefix: str) -> list[str]:
    """The neighbours arp -a lists on one subnet."""
    neighbours = []
    for line in lines:
        match = IPV4_ADDRESS.search(line)
        if match and match.group(1).startswith(prefix) and match.group(1) not in neighbours:
            neighbours.append(match.group(1))
    return neighbours


def parse_netstat(lines: list[str], port: int) -> bool:
    """Whether anything is connected to the Rocket link's port on this laptop."""
    local_port = f":{port}"
    for line in lines:
        columns = line.split()
        if len(columns) < 4:
            continue
        if columns[1].endswith(local_port) and DEVELOPER_NETWORK["gcs_established_text"] in line:
            return True
    return False


def parse_addresses(lines: list[str]) -> dict[str, str]:
    """Interface -> its first IPv4 address, from ip -br addr."""
    addresses = {}
    for line in lines:
        match = ADDRESS_LINE.match(line)
        if match and match.group(1) not in addresses:
            addresses[match.group(1)] = match.group(3)
    return addresses


def parse_neighbours(lines: list[str]) -> list[str]:
    """The neighbours ip neigh actually has a hardware address for."""
    neighbours = []
    for line in lines:
        if NEIGHBOUR_KNOWN_MARK not in line or NEIGHBOUR_FAILED_MARK in line:
            continue
        match = IPV4_ADDRESS.search(line)
        if match:
            neighbours.append(match.group(1))
    return neighbours


def split_sections(lines: list[str]) -> dict[str, list[str]]:
    """Cut the Pi's one answer back into parts by its marker lines.

    Whatever came before the first marker is the address listing. A bare
    marker ends a ping block and stays inside the ping section.
    """
    sections: dict[str, list[str]] = {ADDRESSES_SECTION: []}
    current = ADDRESSES_SECTION
    for line in lines:
        name = line.strip()[len(SECTION_PREFIX):]
        if line.startswith(SECTION_PREFIX) and name in KNOWN_SECTIONS:
            current = name
            sections[current] = []
            continue
        sections[current].append(line)
    return sections


def split_ping_blocks(lines: list[str]) -> dict[str, list[str]]:
    """Host -> the lines ping printed for it."""
    blocks: dict[str, list[str]] = {}
    current = None
    for line in lines:
        if line.startswith(PING_HOST_PREFIX):
            current = line[len(PING_HOST_PREFIX):].strip()
            blocks[current] = []
        elif line.strip() == SECTION_PREFIX:
            current = None
        elif current is not None:
            blocks[current].append(line)
    return blocks


@dataclass
class NetworkReport:
    """Both sides of the ping test. None means not asked or not answered yet."""

    gcs_addresses: list[str] = field(default_factory=list)
    gcs_ping: dict[str, float | None] = field(default_factory=dict)
    gcs_neighbours: list[str] | None = None
    rocket_client_seen: bool | None = None

    pi_reached: bool | None = None
    pi_failure: str | None = None
    pi_addresses: dict[str, str] = field(default_factory=dict)
    pi_ping: dict[str, float | None] = field(default_factory=dict)
    pi_neighbours: list[str] | None = None
    pi_link_socket_seen: bool | None = None

    def gcs_rocket_address(self) -> str | None:
        for address in self.gcs_addresses:
            if address.startswith(DEVELOPER_NETWORK["gcs_rocket_subnet"]):
                return address
        return None

    def pi_siyi_address(self) -> str | None:
        for address in self.pi_addresses.values():
            if address.startswith(DEVELOPER_NETWORK["siyi_subnet"]):
                return address
        return None

    def read_gcs_addresses(self, lines: list[str]) -> None:
        self.gcs_addresses = parse_ipconfig(lines)

    def read_pi_answer(self, lines: list[str], exit_code: int) -> None:
        """The one ssh answer, section by section."""
        sections = split_sections(lines)
        if NEIGHBOURS_SECTION not in sections:
            self.pi_reached = False
            if lines:
                self.pi_failure = lines[-1]
            else:
                self.pi_failure = str(exit_code)
            return
        self.pi_reached = True
        self.pi_addresses = parse_addresses(sections[ADDRESSES_SECTION])
        self.pi_neighbours = parse_neighbours(sections[NEIGHBOURS_SECTION])
        for host, block in split_ping_blocks(sections.get(PING_SECTION, [])).items():
            self.pi_ping[host] = parse_pi_ping(block)
        self.pi_link_socket_seen = any(line.strip() for line in sections.get(SOCKET_SECTION, []))
