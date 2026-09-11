"""What the ping test found, and how each answer is read.

Two sides answer: this laptop, one process per question, and the Pasifik's
Pi, one ssh call whose answer is cut back into parts by marker lines. The
report is plain data — the network table draws it and the diagnosis reads it.
"""

import re
import statistics
from dataclasses import dataclass, field

from competitions.international_uav.config import DEVELOPER_NETWORK
from competitions.international_uav.dev.wifi_state import parse_addresses, split_sections

IPV4_ADDRESS = re.compile(r"(\d+\.\d+\.\d+\.\d+)")
# A line of ipconfig naming an address, in any language Windows speaks here.
IPV4_LINE_MARK = "IPv4"
# One key of the Pasifik's link block: `  address_rocket: "192.168.1.30"`.
CONFIG_LINE = re.compile(r'^\s*(\w+):\s*"([^"]*)"')
# ip neigh names a neighbour it has a hardware address for with this.
NEIGHBOUR_KNOWN_MARK = "lladdr"
NEIGHBOUR_FAILED_MARK = "FAILED"
# The section names pi_commands in developer.toml announces.
SECTION_ADDR = "addr"
SECTION_CONFIG = "config"
SECTION_ROCKET_GROUND = "rocket_ground"
SECTION_ROCKET_AIR = "rocket_air"
SECTION_LAPTOP_DIALLED = "laptop_dialled"
SECTION_LAPTOP_ACTUAL = "laptop_actual"
SECTION_CAMERA = "camera"
SECTION_NEIGHBOURS = "neigh"
SECTION_ROCKET_LINK = "rocket"
CONFIG_CONNECTION = "connection"
CONFIG_ADDRESS_ROCKET = "address_rocket"


@dataclass
class PingResult:
    sent: int
    received: int
    average_ms: float | None

    def answered(self) -> bool:
        return self.received > 0


def parse_ping(lines: list[str], reply_pattern: str, time_pattern: str) -> PingResult:
    """Count the replies and average their times; the count sent is the config's."""
    times = []
    replies = 0
    time_regex = re.compile(time_pattern)
    for line in lines:
        if reply_pattern.lower() in line.lower():
            replies += 1
        match = time_regex.search(line)
        if match:
            times.append(float(match.group(1)))
    average_ms = None
    if times:
        average_ms = statistics.fmean(times)
    return PingResult(DEVELOPER_NETWORK["ping_count"], replies, average_ms)


def parse_gcs_ping(lines: list[str]) -> PingResult:
    return parse_ping(
        lines, DEVELOPER_NETWORK["gcs_reply_pattern"], DEVELOPER_NETWORK["gcs_time_pattern"]
    )


def parse_pi_ping(lines: list[str]) -> PingResult:
    return parse_ping(
        lines, DEVELOPER_NETWORK["pi_reply_pattern"], DEVELOPER_NETWORK["pi_time_pattern"]
    )


def parse_ipconfig(lines: list[str]) -> list[str]:
    addresses = []
    for line in lines:
        if IPV4_LINE_MARK not in line:
            continue
        match = IPV4_ADDRESS.search(line)
        if match:
            addresses.append(match.group(1))
    return addresses


def addresses_on(addresses: list[str], prefix: str) -> list[str]:
    return [address for address in addresses if address.startswith(prefix)]


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


def parse_serial_ports(lines: list[str], port: str) -> bool:
    return any(line.strip() == port for line in lines)


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


@dataclass
class NetworkReport:
    """Both sides of the ping test. None means not asked or not answered yet."""

    gcs_addresses: list[str] = field(default_factory=list)
    gcs_rocket_address: str | None = None
    gcs_rocket_ground: PingResult | None = None
    gcs_rocket_air: PingResult | None = None
    gcs_pasifik: PingResult | None = None
    gcs_agents: dict[int, PingResult] = field(default_factory=dict)
    gcs_neighbours: list[str] | None = None
    rocket_client_connected: bool | None = None
    esp_port_present: bool | None = None

    pi_reached: bool | None = None
    pi_failure: str | None = None
    pi_addresses: dict[str, str] = field(default_factory=dict)
    pi_connection: str | None = None
    pi_dialled_address: str | None = None
    pi_rocket_ground: PingResult | None = None
    pi_rocket_air: PingResult | None = None
    pi_laptop_dialled: PingResult | None = None
    pi_laptop_actual: PingResult | None = None
    pi_camera: PingResult | None = None
    pi_neighbours: list[str] | None = None
    pi_rocket_link: bool | None = None

    def pi_camera_address(self) -> str | None:
        for address in self.pi_addresses.values():
            if address.startswith(DEVELOPER_NETWORK["camera_subnet_prefix"]):
                return address
        return None

    def read_gcs_addresses(self, lines: list[str]) -> None:
        self.gcs_addresses = parse_ipconfig(lines)
        on_rocket_subnet = addresses_on(self.gcs_addresses, DEVELOPER_NETWORK["rocket_subnet_prefix"])
        if on_rocket_subnet:
            self.gcs_rocket_address = on_rocket_subnet[0]

    def read_pi_answer(self, lines: list[str], exit_code: int) -> None:
        """The one ssh answer, section by section."""
        sections = split_sections(lines)
        if SECTION_ADDR not in sections:
            self.pi_reached = False
            if lines:
                self.pi_failure = lines[-1]
            else:
                self.pi_failure = str(exit_code)
            return
        self.pi_reached = True
        self.pi_addresses = parse_addresses(sections[SECTION_ADDR])
        for line in sections.get(SECTION_CONFIG, []):
            match = CONFIG_LINE.match(line)
            if match and match.group(1) == CONFIG_CONNECTION:
                self.pi_connection = match.group(2)
            elif match and match.group(1) == CONFIG_ADDRESS_ROCKET:
                self.pi_dialled_address = match.group(2)
        self.pi_rocket_ground = parse_pi_ping(sections.get(SECTION_ROCKET_GROUND, []))
        self.pi_rocket_air = parse_pi_ping(sections.get(SECTION_ROCKET_AIR, []))
        self.pi_laptop_dialled = parse_pi_ping(sections.get(SECTION_LAPTOP_DIALLED, []))
        if SECTION_LAPTOP_ACTUAL in sections:
            self.pi_laptop_actual = parse_pi_ping(sections[SECTION_LAPTOP_ACTUAL])
        self.pi_camera = parse_pi_ping(sections.get(SECTION_CAMERA, []))
        self.pi_neighbours = parse_neighbours(sections.get(SECTION_NEIGHBOURS, []))
        self.pi_rocket_link = any(line.strip() for line in sections.get(SECTION_ROCKET_LINK, []))
