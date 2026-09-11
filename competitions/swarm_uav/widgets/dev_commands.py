"""What the DEV tab's buttons do on the Pis: one ssh per ticked drone,
reported in the command output as it goes.

A mixin on DevPanel, so these keep using self.drone_names,
self.drone_checkboxes and self.output_terminal. START and STOP go to this
laptop instead while SIMULATION is ticked (dev_local.py).
"""

from datetime import date

from PyQt6.QtWidgets import QMessageBox

from competitions.swarm_uav.config import DEVELOPER_TEXT
from competitions.swarm_uav.dev import (
    LocalProcess,
    SshSession,
    board_reboot,
    log_day_folder,
    logs_fetch,
    node_start,
    node_stop,
    pps_check,
    repository_checkout,
    repository_pull,
    repository_push,
    repository_restore,
)

SUCCESS_EXIT_CODE = 0


class DevCommandsMixin:
    """The START, STOP, PPS CHECK, GET LOGS, REBOOT, PULL, PUSH, CHECKOUT and RESTORE buttons."""

    def ticked_drones(self) -> list[tuple[int, str]]:
        return [
            (vehicle_id, vehicle_name)
            for vehicle_id, vehicle_name in self.drone_names.items()
            if self.drone_checkboxes[vehicle_id].isChecked()
        ]

    def ticked_drone_ids(self) -> list[int]:
        return [vehicle_id for vehicle_id, vehicle_name in self.ticked_drones()]

    def selected_drones(self) -> list[tuple[int, str]]:
        """The ticked drones, or none of them and a line saying so."""
        selected = self.ticked_drones()
        if not selected:
            self.append_output(DEVELOPER_TEXT["no_selection_text"])
        return selected

    def confirmed_drones(self, title: str, question: str) -> list[tuple[int, str]]:
        """The ticked drones, once the operator has said yes to the question."""
        selected = self.selected_drones()
        if not selected:
            return []
        vehicle_names = ", ".join(vehicle_name for vehicle_id, vehicle_name in selected)
        answer = QMessageBox.question(
            self,
            title,
            question.format(vehicles=vehicle_names),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return []
        return selected

    # The buttons

    def start_nodes(self) -> None:
        """The Pis, or this laptop while SIMULATION is ticked.

        The Pis do not read the local config files, so a switch that could not
        be written only stops a local start.
        """
        switch_written = self.write_simulation_mode()
        if self.simulation_checkbox.isChecked():
            if switch_written:
                self.start_local_nodes()
            return
        for vehicle_id, vehicle_name in self.selected_drones():
            self.watch_command(
                vehicle_name, DEVELOPER_TEXT["action_start"], node_start(vehicle_id, self)
            )

    def stop_nodes(self) -> None:
        """A node started here stops whatever the box says; the Pis only when it is off."""
        selected = self.selected_drones()
        self.stop_local_nodes(selected)
        if self.simulation_checkbox.isChecked():
            return
        for vehicle_id, vehicle_name in selected:
            self.watch_command(
                vehicle_name, DEVELOPER_TEXT["action_stop"], node_stop(vehicle_id, self)
            )

    def check_pps(self) -> None:
        for vehicle_id, vehicle_name in self.selected_drones():
            self.watch_command(
                vehicle_name, DEVELOPER_TEXT["action_pps_check"], pps_check(vehicle_id, self)
            )

    def fetch_logs(self) -> None:
        """Copy today's logs off the Pis, so a flight can be read here right after it."""
        flight_day = date.today()
        action_text = DEVELOPER_TEXT["action_logs"].format(day=log_day_folder(flight_day))
        for vehicle_id, vehicle_name in self.selected_drones():
            self.watch_command(
                vehicle_name, action_text, logs_fetch(vehicle_id, flight_day, self)
            )

    def pull_repositories(self) -> None:
        for vehicle_id, vehicle_name in self.selected_drones():
            self.watch_command(
                vehicle_name, DEVELOPER_TEXT["action_pull"], repository_pull(vehicle_id, self)
            )

    def push_repositories(self) -> None:
        """Send the branch open here to the Pis, for a WiFi with no internet.

        The one button here that runs on this laptop rather than on the Pi:
        the commits are here, so it is a git here that sends them over.
        """
        for vehicle_id, vehicle_name in self.selected_drones():
            self.watch_command(
                vehicle_name, DEVELOPER_TEXT["action_push"], repository_push(vehicle_id, self)
            )

    def reboot_boards(self) -> None:
        """Reboot the Pis themselves, once the operator has said so twice."""
        selected = self.confirmed_drones(
            DEVELOPER_TEXT["reboot_title"], DEVELOPER_TEXT["reboot_question"]
        )
        for vehicle_id, vehicle_name in selected:
            self.watch_command(
                vehicle_name, DEVELOPER_TEXT["action_reboot"], board_reboot(vehicle_id, self)
            )

    def restore_repositories(self) -> None:
        """Throw away the edits on the Pis, once the operator has said so twice."""
        selected = self.confirmed_drones(
            DEVELOPER_TEXT["restore_title"], DEVELOPER_TEXT["restore_question"]
        )
        for vehicle_id, vehicle_name in selected:
            self.watch_command(
                vehicle_name,
                DEVELOPER_TEXT["action_restore"],
                repository_restore(vehicle_id, self),
            )

    def checkout_branches(self) -> None:
        branch = self.branch_input.text().strip()
        if not branch:
            self.append_output(DEVELOPER_TEXT["no_branch_text"])
            return
        action_text = DEVELOPER_TEXT["action_checkout"].format(branch=branch)
        for vehicle_id, vehicle_name in self.selected_drones():
            self.watch_command(
                vehicle_name, action_text, repository_checkout(vehicle_id, branch, self)
            )

    # Running one command and showing what came back

    def watch_command(
        self, vehicle_name: str, action_text: str, session: SshSession | LocalProcess
    ) -> None:
        """Run one command, put its output in the terminal, say how it ended.

        The session is only started once everything is listening: a Pi that is
        off reports its failure from inside start().
        """
        self.command_sessions.append(session)
        self.append_output(
            DEVELOPER_TEXT["command_sent"].format(vehicle=vehicle_name, action=action_text)
        )
        session.line_received.connect(
            lambda line: self.append_output(
                DEVELOPER_TEXT["output_line"].format(vehicle=vehicle_name, line=line)
            )
        )
        session.finished.connect(
            lambda exit_code: self.report_command(vehicle_name, action_text, exit_code, session)
        )
        session.start()

    def report_command(
        self,
        vehicle_name: str,
        action_text: str,
        exit_code: int,
        session: SshSession | LocalProcess,
    ) -> None:
        if exit_code == SUCCESS_EXIT_CODE:
            result_text = DEVELOPER_TEXT["command_done"]
        else:
            result_text = DEVELOPER_TEXT["command_failed"]
        self.append_output(
            result_text.format(vehicle=vehicle_name, action=action_text, exit_code=exit_code)
        )
        self.command_sessions.remove(session)
        session.deleteLater()
