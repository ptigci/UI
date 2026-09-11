"""The shell commands the DEV tab runs, filled in for one vehicle.

A vehicle is a Pi with a repository, an app folder and a systemd unit on it;
the Pasifik and the agents differ only in those and in how they are reached.
Every template comes from config/developer.toml, so a moved repository or a
renamed unit is one edit there and nothing here changes. Everything that came
from the operator — a branch name, a network name, a password — is quoted for
the Pi's shell before it goes in.
"""

import shlex
from dataclasses import dataclass

from competitions.international_uav.config import (
    DEVELOPER_AGENTS,
    DEVELOPER_COMMANDS,
    DEVELOPER_NETWORK,
    DEVELOPER_PASIFIK,
    DEVELOPER_PUSH,
    DEVELOPER_SSH_OPTIONS,
    DEVELOPER_SSH_PROGRAM,
    DEVELOPER_SUDO_PASSWORD,
    DEVELOPER_TEXT,
    DEVELOPER_WIFI,
)

SSH_CONNECTIONS = ("rocket", "wifi")
if DEVELOPER_PASIFIK["ssh_connection"] not in SSH_CONNECTIONS:
    raise ValueError(
        f"developer.pasifik.ssh_connection must be one of {SSH_CONNECTIONS}, "
        f"not '{DEVELOPER_PASIFIK['ssh_connection']}'."
    )

NO_ARGUMENTS = ""
MILLISECONDS_PER_SECOND = 1000


@dataclass(frozen=True)
class Vehicle:
    """One companion computer, and what the tab needs to know to run it."""

    name: str
    host: str
    repository: str
    app: str
    unit: str
    start_arguments: str
    is_pasifik: bool
    agent_id: int | None = None


def pasifik_vehicle() -> Vehicle:
    """The Pasifik, reached the way developer.toml says."""
    host = DEVELOPER_PASIFIK[f"{DEVELOPER_PASIFIK['ssh_connection']}_host"]
    return Vehicle(
        DEVELOPER_TEXT["pasifik_name"], host, DEVELOPER_PASIFIK["repository_path"],
        DEVELOPER_PASIFIK["app"], DEVELOPER_PASIFIK["unit_name"], NO_ARGUMENTS, True,
    )


def agent_vehicle(agent_id: int) -> Vehicle:
    """One swarm agent; its node takes its id on the command line."""
    return Vehicle(
        DEVELOPER_TEXT["agent_name"].format(drone_id=agent_id),
        DEVELOPER_AGENTS["host_pattern"].format(drone_id=agent_id),
        DEVELOPER_AGENTS["repository_path"], DEVELOPER_AGENTS["app"],
        DEVELOPER_AGENTS["unit_name"], str(agent_id), False, agent_id,
    )


def fill(template_name: str, vehicle: Vehicle, **values) -> str:
    return DEVELOPER_COMMANDS[template_name].format(
        unit=vehicle.unit, repository=vehicle.repository, app=vehicle.app,
        arguments=vehicle.start_arguments, **values,
    )


def start_command(vehicle: Vehicle) -> str:
    return fill("start", vehicle)


def stop_command(vehicle: Vehicle) -> str:
    return fill("stop", vehicle)


def is_active_command(vehicle: Vehicle) -> str:
    return fill("is_active", vehicle)


def monitor_command(vehicle: Vehicle) -> str:
    return fill("monitor", vehicle)


def pull_command(vehicle: Vehicle) -> str:
    return fill("pull", vehicle)


def push_arguments(vehicle: Vehicle) -> list[str]:
    """The git push that sends this laptop's branch to one Pi, argument by argument."""
    return [
        argument.format(host=vehicle.host, repository=vehicle.repository)
        for argument in DEVELOPER_PUSH["arguments"]
    ]


def push_environment() -> dict:
    """git starts its own ssh, so it gets the one the other commands run with."""
    ssh_command = " ".join([DEVELOPER_SSH_PROGRAM, *DEVELOPER_SSH_OPTIONS])
    return {DEVELOPER_PUSH["ssh_variable"]: ssh_command}


def restore_command(vehicle: Vehicle) -> str:
    return fill("restore", vehicle)


def checkout_command(vehicle: Vehicle, branch: str) -> str:
    return fill("checkout", vehicle, branch=shlex.quote(branch))


def reboot_command(vehicle: Vehicle) -> str:
    """The reboot, run under sudo the way the Pis are set up to accept it."""
    if DEVELOPER_SUDO_PASSWORD:
        sudo_prefix = DEVELOPER_COMMANDS["sudo_prefix_with_password"].format(
            password=shlex.quote(DEVELOPER_SUDO_PASSWORD)
        )
    else:
        sudo_prefix = DEVELOPER_COMMANDS["sudo_prefix"]
    return fill("reboot", vehicle, sudo=sudo_prefix)


def wifi_state_command() -> str:
    return DEVELOPER_COMMANDS["wifi_state"]


def wifi_scan_command() -> str:
    return DEVELOPER_COMMANDS["wifi_scan"]


def wifi_connect_command(ssid: str, password: str) -> str:
    if password:
        return DEVELOPER_COMMANDS["wifi_connect"].format(
            ssid=shlex.quote(ssid), password=shlex.quote(password)
        )
    return DEVELOPER_COMMANDS["wifi_connect_open"].format(ssid=shlex.quote(ssid))


def connectivity_command() -> str:
    return DEVELOPER_COMMANDS["connectivity"]


def pi_network_command(vehicle: Vehicle, laptop_address: str | None) -> str:
    """Everything the Pasifik's Pi is asked in the ping test, in one ssh call.

    Each part is announced by a marker line, so the one answer can be cut back
    into parts on the way in. Without the laptop's actual Rocket-subnet
    address the ping to it is left out rather than sent to nobody.
    """
    values = dict(
        DEVELOPER_NETWORK,
        count=DEVELOPER_NETWORK["ping_count"], timeout=DEVELOPER_NETWORK["ping_timeout_s"],
        repository=vehicle.repository, app=vehicle.app, laptop_address=laptop_address,
    )
    marker = DEVELOPER_WIFI["section_marker"]
    parts = []
    for key, template in DEVELOPER_NETWORK["pi_commands"].items():
        if key == "laptop_actual" and laptop_address is None:
            continue
        parts.append(f"echo {shlex.quote(marker + key)}; {template.format(**values)}")
    return "; ".join(parts)


def gcs_ping_arguments(address: str) -> list[str]:
    """The local ping, as a program and its arguments."""
    timeout_ms = DEVELOPER_NETWORK["ping_timeout_s"] * MILLISECONDS_PER_SECOND
    return [
        part.format(count=DEVELOPER_NETWORK["ping_count"], timeout_ms=timeout_ms, address=address)
        for part in DEVELOPER_NETWORK["gcs_ping"]
    ]
