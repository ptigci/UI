"""Developer module: the aircraft software as it runs on the VTOL's Pi.

The Pi is reachable over SSH, and these functions are everything the DEV tab
can ask of it: start the node, stop it, ask whether it is running, watch its
log, bring the checkout up to date or throw its edits away, reboot the board,
and look at and connect its wifi. Each returns the session for that command,
ready but not running: connect to its signals, then start it. A host that is
off reports its failure the moment it is started, so a caller that starts
first misses it.

Beside the Pi: the ground services as a local process, the vtol node as a
local process for a simulation, the test mission that stands in for Mission
Planner against SITL, the push that sends this laptop's branch to the Pi, the
simulation switch in its config, the ping test that asks both sides of the
Rocket link what they can see, the probes that measure the mission path end to
end, and the diagnosis that reads both.
"""

from competitions.suas.config import DEVELOPER_LOCAL, DEVELOPER_PUSH
from competitions.suas.dev.diagnosis import diagnose
from competitions.suas.dev.link_probe import LinkProbe, LinkTestResult, ProbeResult
from competitions.suas.dev.local_process import LocalProcess, local_app
from competitions.suas.dev.log_line import decode_log_line
from competitions.suas.dev.network_probe import NetworkProbe
from competitions.suas.dev.network_report import NetworkReport
from competitions.suas.dev.simulation_switch import (
    read_simulation_mode,
    set_simulation_mode,
)
from competitions.suas.dev.ssh_session import SshSession
from competitions.suas.dev.vtol_commands import (
    checkout_command,
    connectivity_command,
    is_active_command,
    monitor_command,
    pi_network_command,
    pull_command,
    push_arguments,
    push_environment,
    reboot_command,
    restore_command,
    start_command,
    stop_command,
    vtol_host,
    wifi_connect_command,
    wifi_scan_command,
)
from competitions.suas.dev.wifi_state import (
    WifiNetwork,
    WifiState,
    parse_connectivity,
    parse_wifi_scan,
)

# What the log shows instead of a command that carries a password.
WIFI_CONNECT_SHOWN_AS = "nmcli dev wifi connect ..."
REBOOT_SHOWN_AS = "reboot"


def vtol_start(parent=None) -> SshSession:
    """Run the node as a systemd unit, so it outlives this connection."""
    return SshSession(vtol_host(), start_command(), parent)


def vtol_stop(parent=None) -> SshSession:
    """SIGTERM, which main.py handles: the node shuts down instead of dying."""
    return SshSession(vtol_host(), stop_command(), parent)


def vtol_status(parent=None) -> SshSession:
    """Whether the unit is active, as systemd sees it."""
    return SshSession(vtol_host(), is_active_command(), parent)


def vtol_monitor(parent=None) -> SshSession:
    """Follow the node's journal, including what it printed before now."""
    return SshSession(vtol_host(), monitor_command(), parent)


def vtol_reboot(parent=None) -> SshSession:
    """Reboot the Pi itself. The node does not come back with it."""
    return SshSession(vtol_host(), reboot_command(), parent, REBOOT_SHOWN_AS)


def repository_pull(parent=None) -> SshSession:
    return SshSession(vtol_host(), pull_command(), parent)


def repository_push(parent=None) -> LocalProcess:
    """Send the branch open on this laptop into the Pi's checkout, over ssh.

    This one runs here rather than on the Pi: it is this checkout that holds
    the commits, and the Pi needs no way out to GitHub for it.
    """
    return LocalProcess(
        DEVELOPER_PUSH["git_program"],
        push_arguments(),
        DEVELOPER_PUSH["directory"],
        push_environment(),
        parent,
    )


def repository_checkout(branch: str, parent=None) -> SshSession:
    return SshSession(vtol_host(), checkout_command(branch), parent)


def repository_restore(parent=None) -> SshSession:
    """Drop every uncommitted edit on the Pi. Cannot be undone."""
    return SshSession(vtol_host(), restore_command(), parent)


def connectivity_check(parent=None) -> SshSession:
    """The Pi's devices and whether it has a way out to the internet."""
    return SshSession(vtol_host(), connectivity_command(), parent)


def wifi_scan(parent=None) -> SshSession:
    return SshSession(vtol_host(), wifi_scan_command(), parent)


def wifi_connect(ssid: str, password: str, parent=None) -> SshSession:
    """Join one network; the password never reaches the log."""
    return SshSession(vtol_host(), wifi_connect_command(ssid, password), parent, WIFI_CONNECT_SHOWN_AS)


def pi_network_report(hosts: list[str], parent=None) -> SshSession:
    """The Pi's addresses, neighbours, pings to the hosts and its link socket."""
    return SshSession(vtol_host(), pi_network_command(hosts), parent)


def ground_services_start(parent=None) -> LocalProcess:
    """The ground services on this laptop, ready to start."""
    return local_app(DEVELOPER_LOCAL["computer"], parent)


def vtol_start_local(parent=None) -> LocalProcess:
    """The vtol node on this laptop, against SITL. Ready to start."""
    return local_app(DEVELOPER_LOCAL["vtol"], parent)


def test_mission_start(parent=None) -> LocalProcess:
    """The operator's job against SITL: upload the mission, arm, start AUTO."""
    return local_app(DEVELOPER_LOCAL["test_mission"], parent)


__all__ = [
    "LinkProbe",
    "LinkTestResult",
    "LocalProcess",
    "NetworkProbe",
    "NetworkReport",
    "ProbeResult",
    "SshSession",
    "WifiNetwork",
    "WifiState",
    "connectivity_check",
    "decode_log_line",
    "diagnose",
    "ground_services_start",
    "parse_connectivity",
    "parse_wifi_scan",
    "pi_network_report",
    "read_simulation_mode",
    "repository_checkout",
    "repository_pull",
    "repository_push",
    "repository_restore",
    "set_simulation_mode",
    "test_mission_start",
    "vtol_host",
    "vtol_monitor",
    "vtol_reboot",
    "vtol_start",
    "vtol_start_local",
    "vtol_status",
    "vtol_stop",
    "wifi_connect",
    "wifi_scan",
]
