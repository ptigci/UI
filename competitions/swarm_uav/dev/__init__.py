"""Developer module: the drone nodes as they run on the companion Pis.

Each drone's software runs on its own Raspberry Pi, reachable over SSH. These
functions are everything the DEV tab can ask of one: start the node, stop it,
watch its log, bring the checkout up to date or throw its edits away, and
reboot the board. Each of
those returns the session for that command, ready but not running: connect to
its signals, then start it. A host that is off reports its failure the moment
it is started, so a caller that starts first misses it. decode_log_line turns
what comes back into something a terminal can show.

Beside the Pis: the computer node as a local process, the drone nodes as local
processes for a simulation, the push that sends this laptop's branch to a Pi,
the copy that brings a flight day's logs back from one, and the simulation
switch in their config files.
"""

from datetime import date

from competitions.swarm_uav.config import DEVELOPER_LOCAL, DEVELOPER_LOGS, DEVELOPER_PUSH
from competitions.swarm_uav.dev.local_process import LocalProcess, local_app
from competitions.swarm_uav.dev.log_fetch import fetch_arguments, log_day_folder
from competitions.swarm_uav.dev.log_line import decode_log_line
from competitions.swarm_uav.dev.node_commands import (
    checkout_command,
    host_for,
    monitor_command,
    pps_check_command,
    pull_command,
    push_arguments,
    push_environment,
    reboot_command,
    restore_command,
    start_command,
    stop_command,
)
from competitions.swarm_uav.dev.simulation_switch import set_simulation_mode
from competitions.swarm_uav.dev.ssh_session import SshSession


def node_start_local(drone_id: int, parent=None) -> LocalProcess:
    """The drone node on this laptop, against SITL. Ready to start."""
    return local_app(DEVELOPER_LOCAL["drone"], [str(drone_id)], parent)


def computer_start(parent=None) -> LocalProcess:
    """The computer node on this laptop, ready to start."""
    return local_app(DEVELOPER_LOCAL["computer"], [], parent)


def node_start(drone_id: int, parent=None) -> SshSession:
    """Run the node as a systemd unit, so it outlives this connection."""
    return SshSession(host_for(drone_id), start_command(drone_id), parent)


def node_stop(drone_id: int, parent=None) -> SshSession:
    """SIGTERM, which main.py handles — the node shuts down instead of dying."""
    return SshSession(host_for(drone_id), stop_command(), parent)


def node_monitor(drone_id: int, parent=None) -> SshSession:
    """Follow the node's journal, including what it printed before now."""
    return SshSession(host_for(drone_id), monitor_command(), parent)


def board_reboot(drone_id: int, parent=None) -> SshSession:
    """Reboot the Pi itself. The node does not come back with it."""
    return SshSession(host_for(drone_id), reboot_command(), parent)


def pps_check(drone_id: int, parent=None) -> SshSession:
    """Walk the Pi's PPS chain and say what is wrong, fixing what software can."""
    return SshSession(host_for(drone_id), pps_check_command(), parent)


def logs_fetch(drone_id: int, flight_day: date, parent=None) -> LocalProcess:
    """Bring one day's flight logs off the Pi. Runs here, like the push."""
    return LocalProcess(
        DEVELOPER_LOGS["scp_program"],
        fetch_arguments(host_for(drone_id), flight_day),
        DEVELOPER_LOGS["destination"],
        {},
        parent,
    )


def repository_pull(drone_id: int, parent=None) -> SshSession:
    return SshSession(host_for(drone_id), pull_command(), parent)


def repository_push(drone_id: int, parent=None) -> LocalProcess:
    """Send the branch open on this laptop into the Pi's checkout, over ssh.

    This one runs here rather than on the Pi: it is this checkout that holds
    the commits, and a field WiFi has no way out to GitHub for a pull.
    """
    return LocalProcess(
        DEVELOPER_PUSH["git_program"],
        push_arguments(drone_id),
        DEVELOPER_PUSH["directory"],
        push_environment(),
        parent,
    )


def repository_checkout(drone_id: int, branch: str, parent=None) -> SshSession:
    return SshSession(host_for(drone_id), checkout_command(branch), parent)


def repository_restore(drone_id: int, parent=None) -> SshSession:
    """Drop every uncommitted edit on the Pi. Cannot be undone."""
    return SshSession(host_for(drone_id), restore_command(), parent)
