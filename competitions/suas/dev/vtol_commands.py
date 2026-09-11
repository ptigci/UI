"""The shell commands the DEV tab runs on the VTOL's Pi, filled in.

Every template comes from config/developer.toml, so a moved repository or a
renamed unit is one edit there and nothing here changes. Everything that came
from the operator — a branch name, a network name, a password — is quoted for
the Pi's shell before it goes in.
"""

import shlex

from competitions.suas.config import (
    DEVELOPER_COMMANDS,
    DEVELOPER_NETWORK,
    DEVELOPER_PUSH,
    DEVELOPER_SSH_OPTIONS,
    DEVELOPER_SSH_PROGRAM,
    DEVELOPER_SUDO_PASSWORD,
    DEVELOPER_VTOL,
)

SSH_CONNECTIONS = ("ethernet", "wifi")
if DEVELOPER_VTOL["ssh_connection"] not in SSH_CONNECTIONS:
    raise ValueError(
        f"developer.vtol.ssh_connection must be one of {SSH_CONNECTIONS}, "
        f"not '{DEVELOPER_VTOL['ssh_connection']}'."
    )

HOST_SEPARATOR = "@"
MILLISECONDS_PER_SECOND = 1000


def vtol_host() -> str:
    """The Pi, reached the way developer.toml says."""
    return DEVELOPER_VTOL[f"{DEVELOPER_VTOL['ssh_connection']}_host"]


def vtol_address() -> str:
    """The host without its user name, for a ping."""
    return vtol_host().split(HOST_SEPARATOR)[-1]


def fill(template_name: str, **values) -> str:
    return DEVELOPER_COMMANDS[template_name].format(
        unit=DEVELOPER_VTOL["unit_name"],
        repository=DEVELOPER_VTOL["repository_path"],
        app=DEVELOPER_VTOL["app_directory"],
        **values,
    )


def push_arguments() -> list[str]:
    """The git push that sends this laptop's branch to the Pi, argument by argument."""
    return [
        argument.format(host=vtol_host(), repository=DEVELOPER_VTOL["repository_path"])
        for argument in DEVELOPER_PUSH["arguments"]
    ]


def push_environment() -> dict:
    """git starts its own ssh, so it gets the one the other commands run with."""
    ssh_command = " ".join([DEVELOPER_SSH_PROGRAM, *DEVELOPER_SSH_OPTIONS])
    return {DEVELOPER_PUSH["ssh_variable"]: ssh_command}


def start_command() -> str:
    return fill("start")


def stop_command() -> str:
    return fill("stop")


def is_active_command() -> str:
    return fill("is_active")


def monitor_command() -> str:
    return fill("monitor")


def pull_command() -> str:
    return fill("pull")


def restore_command() -> str:
    return fill("restore")


def checkout_command(branch: str) -> str:
    return fill("checkout", branch=shlex.quote(branch))


def reboot_command() -> str:
    """The reboot, run under sudo the way the Pi is set up to accept it."""
    if DEVELOPER_SUDO_PASSWORD:
        sudo_prefix = DEVELOPER_COMMANDS["sudo_prefix_with_password"].format(
            password=shlex.quote(DEVELOPER_SUDO_PASSWORD)
        )
    else:
        sudo_prefix = DEVELOPER_COMMANDS["sudo_prefix"]
    return fill("reboot", sudo=sudo_prefix)


def connectivity_command() -> str:
    return DEVELOPER_COMMANDS["connectivity"]


def wifi_scan_command() -> str:
    return DEVELOPER_COMMANDS["wifi_scan"]


def wifi_connect_command(ssid: str, password: str) -> str:
    if password:
        return DEVELOPER_COMMANDS["wifi_connect"].format(
            ssid=shlex.quote(ssid), password=shlex.quote(password)
        )
    return DEVELOPER_COMMANDS["wifi_connect_open"].format(ssid=shlex.quote(ssid))


def pi_network_command(hosts: list[str]) -> str:
    """Everything the Pi is asked in the ping test, in one ssh call."""
    return DEVELOPER_COMMANDS["pi_network"].format(
        hosts=" ".join(shlex.quote(host) for host in hosts),
        count=DEVELOPER_NETWORK["ping_count"],
        timeout=int(DEVELOPER_NETWORK["ping_timeout_s"]),
        port=DEVELOPER_NETWORK["link_port"],
    )


def gcs_ping_arguments(address: str) -> list[str]:
    """The local ping, as a program and its arguments."""
    timeout_ms = int(DEVELOPER_NETWORK["ping_timeout_s"] * MILLISECONDS_PER_SECOND)
    return [
        part.format(count=DEVELOPER_NETWORK["ping_count"], timeout_ms=timeout_ms, address=address)
        for part in DEVELOPER_NETWORK["gcs_ping"]
    ]
