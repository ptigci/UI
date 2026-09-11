"""The PING TEST: what this laptop can see, and what the VTOL's Pi can see.

The laptop's side is one local process per question; the Pi's side is one ssh
call, started once the laptop knows its own Rocket-subnet address, because the
Pi is asked to ping that as well as the address the aircraft is configured to
dial. Nothing blocks the Qt thread: the report fills in as each answer lands,
and every one of them is announced so the table can draw what it has.
"""

import logging

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

from competitions.suas.config import DEVELOPER_NETWORK
from competitions.suas.dev.network_report import (
    NetworkReport,
    parse_arp,
    parse_gcs_ping,
    parse_netstat,
)
from competitions.suas.dev.ssh_session import SshSession
from competitions.suas.dev.vtol_commands import (
    gcs_ping_arguments,
    pi_network_command,
    vtol_address,
    vtol_host,
)

logger = logging.getLogger(__name__)

LINE_SEPARATOR = "\n"


def pi_hosts(laptop_address: str | None) -> list[str]:
    """What the Pi pings: both Rockets, the ground address the aircraft dials,
    the laptop's actual address when that is a different one, and the camera."""
    hosts = [
        DEVELOPER_NETWORK["rocket_ground"],
        DEVELOPER_NETWORK["rocket_air"],
        DEVELOPER_NETWORK["link_ground_host"],
    ]
    if laptop_address is not None and laptop_address not in hosts:
        hosts.append(laptop_address)
    hosts.append(DEVELOPER_NETWORK["siyi"])
    return hosts


class NetworkProbe(QObject):
    """One press of PING TEST, from the first process to the last answer."""

    updated = pyqtSignal(object)
    finished = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.report = NetworkReport()
        self.processes: list[QProcess] = []
        self.pi_session: SshSession | None = None
        self.pending = 0

    def start(self) -> None:
        self.report = NetworkReport()
        # The laptop's addresses first: the Pi's questions depend on them.
        self.run_local(DEVELOPER_NETWORK["gcs_addresses"], self.take_gcs_addresses)
        for address in (DEVELOPER_NETWORK["rocket_ground"], DEVELOPER_NETWORK["rocket_air"], vtol_address()):
            self.run_local(
                gcs_ping_arguments(address),
                lambda lines, pinged=address: self.take_gcs_ping(pinged, lines),
            )
        self.run_local(DEVELOPER_NETWORK["gcs_neighbours"], self.take_neighbours)
        self.run_local(DEVELOPER_NETWORK["gcs_rocket_clients"], self.take_rocket_clients)

    def stop(self) -> None:
        for process in self.processes:
            process.kill()
        if self.pi_session is not None:
            self.pi_session.stop()

    # The laptop's side

    def run_local(self, arguments: list[str], take_answer) -> None:
        program, *program_arguments = arguments
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.finished.connect(lambda: self.local_finished(process, take_answer))
        process.errorOccurred.connect(
            lambda error: self.local_failed(process, error, take_answer)
        )
        self.processes.append(process)
        self.pending += 1
        process.start(program, program_arguments)

    def local_finished(self, process: QProcess, take_answer) -> None:
        output = bytes(process.readAllStandardOutput()).decode(errors="replace")
        self.answer_landed(process, take_answer, output.split(LINE_SEPARATOR))

    def local_failed(self, process: QProcess, error, take_answer) -> None:
        if error != QProcess.ProcessError.FailedToStart:
            return
        logger.error(f"Could not start '{process.program()}' for the ping test.")
        self.answer_landed(process, take_answer, [])

    def answer_landed(self, process: QProcess, take_answer, lines: list[str]) -> None:
        if process not in self.processes:
            return  # reported already, or stopped
        self.processes.remove(process)
        process.deleteLater()
        take_answer(lines)
        self.one_done()

    def one_done(self) -> None:
        self.pending -= 1
        self.updated.emit(self.report)
        if self.pending == 0:
            self.finished.emit(self.report)

    def take_gcs_addresses(self, lines: list[str]) -> None:
        self.report.read_gcs_addresses(lines)
        self.ask_pi()

    def take_gcs_ping(self, address: str, lines: list[str]) -> None:
        self.report.gcs_ping[address] = parse_gcs_ping(lines)

    def take_neighbours(self, lines: list[str]) -> None:
        self.report.gcs_neighbours = parse_arp(lines, DEVELOPER_NETWORK["gcs_rocket_subnet"])

    def take_rocket_clients(self, lines: list[str]) -> None:
        self.report.rocket_client_seen = parse_netstat(lines, DEVELOPER_NETWORK["link_port"])

    # The Pi's side

    def ask_pi(self) -> None:
        command = pi_network_command(pi_hosts(self.report.gcs_rocket_address()))
        self.pi_session = SshSession(vtol_host(), command, self)
        self.pending += 1
        self.pi_session.finished.connect(self.take_pi_answer)
        self.pi_session.start()

    def take_pi_answer(self, exit_code: int) -> None:
        session = self.pi_session
        self.pi_session = None
        self.report.read_pi_answer(session.lines, exit_code)
        session.deleteLater()
        self.one_done()
