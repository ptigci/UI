"""Developer module: the vehicle software as it runs on the companion Pis.

The Pasifik's Pi 5 and each agent's Pi 4 are reachable over SSH, and these
functions are everything the DEV tab can ask of one: start the node, stop it,
ask whether it is running, watch its log, bring the checkout up to date or
throw its edits away, reboot the board, and — for the Pasifik — look at and
connect its wifi. Each returns the session for that command, ready but not
running: connect to its signals, then start it. A host that is off reports its
failure the moment it is started, so a caller that starts first misses it.

Beside the Pis: the ground station as a local process, the vehicles as local
processes for a simulation, the push that sends this laptop's branch to a Pi,
and the simulation switch in their config files,
the ping test that asks both sides of the Rocket link what they can see, and
the diagnosis that reads it.
"""

from competitions.international_uav.config import DEVELOPER_LOCAL, DEVELOPER_PUSH
from competitions.international_uav.dev.diagnosis import diagnose
from competitions.international_uav.dev.local_process import LocalProcess, local_app
from competitions.international_uav.dev.log_line import decode_log_line
from competitions.international_uav.dev.network_probe import NetworkProbe
from competitions.international_uav.dev.network_report import NetworkReport, PingResult
from competitions.international_uav.dev.simulation_switch import set_simulation_mode
from competitions.international_uav.dev.ssh_session import SshSession
from competitions.international_uav.dev.vehicle_commands import (
    Vehicle,
    agent_vehicle,
    checkout_command,
    connectivity_command,
    is_active_command,
    monitor_command,
    pasifik_vehicle,
    pull_command,
    push_arguments,
    push_environment,
    reboot_command,
    restore_command,
    start_command,
    stop_command,
    wifi_connect_command,
    wifi_scan_command,
    wifi_state_command,
)
from competitions.international_uav.dev.wifi_state import (
    WifiNetwork,
    WifiState,
    parse_wifi_scan,
    parse_wifi_state,
)

# What the log shows instead of a command that carries a password.
WIFI_CONNECT_SHOWN_AS = "nmcli dev wifi connect ..."
REBOOT_SHOWN_AS = "reboot"


def node_start(vehicle: Vehicle, parent=None) -> SshSession:
    """Run the node as a systemd unit, so it outlives this connection."""
    return SshSession(vehicle.host, start_command(vehicle), parent)


def node_stop(vehicle: Vehicle, parent=None) -> SshSession:
    """SIGTERM, which main.py handles — the node shuts down instead of dying."""
    return SshSession(vehicle.host, stop_command(vehicle), parent)


def node_status(vehicle: Vehicle, parent=None) -> SshSession:
    """Whether the unit is active, as systemd sees it."""
    return SshSession(vehicle.host, is_active_command(vehicle), parent)


def node_monitor(vehicle: Vehicle, parent=None) -> SshSession:
    """Follow the node's journal, including what it printed before now."""
    return SshSession(vehicle.host, monitor_command(vehicle), parent)


def board_reboot(vehicle: Vehicle, parent=None) -> SshSession:
    """Reboot the Pi itself. The node does not come back with it."""
    return SshSession(vehicle.host, reboot_command(vehicle), parent, REBOOT_SHOWN_AS)


def repository_pull(vehicle: Vehicle, parent=None) -> SshSession:
    return SshSession(vehicle.host, pull_command(vehicle), parent)


def repository_push(vehicle: Vehicle, parent=None) -> LocalProcess:
    """Send the branch open on this laptop into the Pi's checkout, over ssh.

    This one runs here rather than on the Pi: it is this checkout that holds
    the commits, and the Pi needs no way out to GitHub for it.
    """
    return LocalProcess(
        DEVELOPER_PUSH["git_program"],
        push_arguments(vehicle),
        DEVELOPER_PUSH["directory"],
        push_environment(),
        parent,
    )


def repository_checkout(vehicle: Vehicle, branch: str, parent=None) -> SshSession:
    return SshSession(vehicle.host, checkout_command(vehicle, branch), parent)


def repository_restore(vehicle: Vehicle, parent=None) -> SshSession:
    """Drop every uncommitted edit on the Pi. Cannot be undone."""
    return SshSession(vehicle.host, restore_command(vehicle), parent)


def wifi_state(vehicle: Vehicle, parent=None) -> SshSession:
    """The Pi's devices, its way out to the internet and its addresses."""
    return SshSession(vehicle.host, wifi_state_command(), parent)


def wifi_scan(vehicle: Vehicle, parent=None) -> SshSession:
    return SshSession(vehicle.host, wifi_scan_command(), parent)


def wifi_connect(vehicle: Vehicle, ssid: str, password: str, parent=None) -> SshSession:
    """Join one network; the password never reaches the log."""
    return SshSession(
        vehicle.host, wifi_connect_command(ssid, password), parent, WIFI_CONNECT_SHOWN_AS
    )


def connectivity_check(vehicle: Vehicle, parent=None) -> SshSession:
    return SshSession(vehicle.host, connectivity_command(), parent)


def ground_start(parent=None) -> LocalProcess:
    """The ground station on this laptop, ready to start."""
    return local_app(DEVELOPER_LOCAL["computer"], [], parent)


def local_node_start(vehicle: Vehicle, parent=None) -> LocalProcess:
    """The vehicle's node on this laptop, against SITL. Ready to start."""
    return local_app(DEVELOPER_LOCAL[vehicle.app], vehicle.start_arguments.split(), parent)


__all__ = [
    "LocalProcess",
    "NetworkProbe",
    "NetworkReport",
    "PingResult",
    "SshSession",
    "Vehicle",
    "WifiNetwork",
    "WifiState",
    "agent_vehicle",
    "board_reboot",
    "connectivity_check",
    "decode_log_line",
    "diagnose",
    "ground_start",
    "local_node_start",
    "node_monitor",
    "node_start",
    "node_status",
    "node_stop",
    "parse_wifi_scan",
    "parse_wifi_state",
    "pasifik_vehicle",
    "repository_checkout",
    "repository_pull",
    "repository_push",
    "repository_restore",
    "set_simulation_mode",
    "wifi_connect",
    "wifi_scan",
    "wifi_state",
]
