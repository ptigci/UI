"""The PING TEST: what this laptop can see, and what the Pasifik's Pi can see.

The laptop's side is one local process per question; the Pi's side is one ssh
call, started once the laptop knows its own Rocket-subnet address, because the
Pi is asked to ping that as well as the address it is configured to dial.
Nothing blocks the Qt thread: the report fills in as each answer lands, and
every one of them is announced so the table can draw what it has.
"""

import logging

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

from competitions.international_uav.config import DEVELOPER_NETWORK
from competitions.international_uav.dev.network_report import (
    NetworkReport,
    parse_arp,
    parse_gcs_ping,
    parse_netstat,
    parse_serial_ports,
)
from competitions.international_uav.dev.ssh_session import SshSession
from competitions.international_uav.dev.vehicle_commands import (
    Vehicle,
    gcs_ping_arguments,
    pi_network_command,
)

logger = logging.getLogger(__name__)

LINE_SEPARATOR = "\n"
HOST_SEPARATOR = "@"


class NetworkProbe(QObject):
    """One press of PING TEST, from the first process to the last answer."""

    updated = pyqtSignal(object)
    finished = pyqtSignal(object)

    def __init__(self, pasifik: Vehicle, agents: list[Vehicle], parent=None) -> None:
        super().__init__(parent)
        self.pasifik = pasifik
        self.agents = agents
        self.report = NetworkReport()
        self.processes: list[QProcess] = []
        self.pi_session: SshSession | None = None
        self.pending = 0

    def start(self) -> None:
        self.report = NetworkReport()
        # The laptop's addresses first: the Pi's questions depend on them.
        self.run_local(DEVELOPER_NETWORK["gcs_addresses"], self.take_gcs_addresses)
        self.run_local(gcs_ping_arguments(DEVELOPER_NETWORK["rocket_ground"]), self.take_rocket_ground)
        self.run_local(gcs_ping_arguments(DEVELOPER_NETWORK["rocket_air"]), self.take_rocket_air)
        self.run_local(gcs_ping_arguments(DEVELOPER_NETWORK["pasifik_pi"]), self.take_pasifik)
        self.run_local(DEVELOPER_NETWORK["gcs_neighbours"], self.take_neighbours)
        self.run_local(DEVELOPER_NETWORK["gcs_rocket_clients"], self.take_rocket_clients)
        self.run_local(DEVELOPER_NETWORK["gcs_serial_ports"], self.take_serial_ports)
        for agent in self.agents:
            host_name = agent.host.split(HOST_SEPARATOR)[-1]
            self.run_local(
                gcs_ping_arguments(host_name),
                lambda lines, agent_id=agent.agent_id: self.take_agent(agent_id, lines),
            )

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

    def take_rocket_ground(self, lines: list[str]) -> None:
        self.report.gcs_rocket_ground = parse_gcs_ping(lines)

    def take_rocket_air(self, lines: list[str]) -> None:
        self.report.gcs_rocket_air = parse_gcs_ping(lines)

    def take_pasifik(self, lines: list[str]) -> None:
        self.report.gcs_pasifik = parse_gcs_ping(lines)

    def take_agent(self, agent_id: int, lines: list[str]) -> None:
        self.report.gcs_agents[agent_id] = parse_gcs_ping(lines)

    def take_neighbours(self, lines: list[str]) -> None:
        self.report.gcs_neighbours = parse_arp(lines, DEVELOPER_NETWORK["rocket_subnet_prefix"])

    def take_rocket_clients(self, lines: list[str]) -> None:
        self.report.rocket_client_connected = parse_netstat(lines, DEVELOPER_NETWORK["rocket_port"])

    def take_serial_ports(self, lines: list[str]) -> None:
        self.report.esp_port_present = parse_serial_ports(lines, DEVELOPER_NETWORK["esp_port"])

    # The Pi's side

    def ask_pi(self) -> None:
        command = pi_network_command(self.pasifik, self.report.gcs_rocket_address)
        self.pi_session = SshSession(self.pasifik.host, command, self)
        self.pending += 1
        self.pi_session.finished.connect(self.take_pi_answer)
        self.pi_session.start()

    def take_pi_answer(self, exit_code: int) -> None:
        session = self.pi_session
        self.pi_session = None
        self.report.read_pi_answer(session.lines, exit_code)
        session.deleteLater()
        self.one_done()
