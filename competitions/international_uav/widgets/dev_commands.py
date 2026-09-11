"""What the DEV tab's buttons do: one ssh per ticked vehicle, reported in the
command output as it goes.

A mixin on DevPanel, so these keep using self.vehicles, self.checkboxes and
self.output_terminal. The Pasifik is asked for its wifi before a pull or a
checkout; without one, the wifi dialog takes over and runs the command itself
once the Pi has a way out. START and STOP go to this laptop instead while
SIMULATION is ticked (dev_local.py).
"""

from competitions.international_uav.config import DEVELOPER_TEXT
from competitions.international_uav.dev import (
    LocalProcess,
    SshSession,
    Vehicle,
    board_reboot,
    node_start,
    node_stop,
    parse_wifi_state,
    repository_checkout,
    repository_pull,
    repository_push,
    repository_restore,
    wifi_state,
)
from competitions.international_uav.widgets.wifi_dialog import WifiDialog

SUCCESS_EXIT_CODE = 0


class DevCommandsMixin:
    """The START, STOP, REBOOT, PULL, PUSH, CHECKOUT and RESTORE buttons."""

    def ticked_vehicles(self) -> list[Vehicle]:
        return [vehicle for vehicle in self.vehicles if self.checkboxes[vehicle.name].isChecked()]

    def ticked_agent_ids(self) -> list[int]:
        return [vehicle.agent_id for vehicle in self.ticked_vehicles() if not vehicle.is_pasifik]

    def selected_vehicles(self) -> list[Vehicle]:
        """The ticked vehicles, or none of them and a line saying so."""
        selected = self.ticked_vehicles()
        if not selected:
            self.append_output(DEVELOPER_TEXT["no_selection_text"])
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
        for vehicle in self.selected_vehicles():
            self.watch_command(vehicle.name, DEVELOPER_TEXT["action_start"], node_start(vehicle, self))

    def stop_nodes(self) -> None:
        """A node started here stops whatever the box says; the Pis only when it is off."""
        selected = self.selected_vehicles()
        self.stop_local_nodes(selected)
        if self.simulation_checkbox.isChecked():
            return
        for vehicle in selected:
            self.watch_command(vehicle.name, DEVELOPER_TEXT["action_stop"], node_stop(vehicle, self))

    def reboot_boards(self) -> None:
        """Reboot the Pis themselves. They take about half a minute to come back."""
        selected = self.selected_vehicles()
        for vehicle in selected:
            self.watch_command(vehicle.name, DEVELOPER_TEXT["action_reboot"], board_reboot(vehicle, self))

    def restore_repositories(self) -> None:
        """Throw away every uncommitted change in the repository on the Pis."""
        selected = self.selected_vehicles()
        for vehicle in selected:
            self.watch_command(
                vehicle.name, DEVELOPER_TEXT["action_restore"], repository_restore(vehicle, self)
            )

    def pull_repositories(self) -> None:
        for vehicle in self.selected_vehicles():
            self.run_with_wifi(
                vehicle, DEVELOPER_TEXT["action_pull"], lambda vehicle=vehicle: repository_pull(vehicle, self)
            )

    def push_repositories(self) -> None:
        """Send the branch open here to the Pis, for a board with no internet.

        The one button here that runs on this laptop rather than on the Pi:
        the commits are here, so it is a git here that sends them over. It
        also skips the wifi check, because a push needs nothing but ssh.
        """
        for vehicle in self.selected_vehicles():
            self.watch_command(
                vehicle.name, DEVELOPER_TEXT["action_push"], repository_push(vehicle, self)
            )

    def checkout_branches(self) -> None:
        branch = self.branch_input.text().strip()
        if not branch:
            self.append_output(DEVELOPER_TEXT["no_branch_text"])
            return
        action_text = DEVELOPER_TEXT["action_checkout"].format(branch=branch)
        for vehicle in self.selected_vehicles():
            self.run_with_wifi(
                vehicle, action_text,
                lambda vehicle=vehicle: repository_checkout(vehicle, branch, self),
            )

    # The Pasifik's wifi, before anything that needs the internet

    def run_with_wifi(self, vehicle: Vehicle, action_text: str, make_session) -> None:
        """The agents are on wifi already; the Pasifik is asked first."""
        if not vehicle.is_pasifik:
            self.watch_command(vehicle.name, action_text, make_session())
            return
        self.append_output(DEVELOPER_TEXT["wifi_checking_text"])
        session = wifi_state(vehicle, self)
        self.command_sessions.append(session)
        session.finished.connect(
            lambda exit_code: self.wifi_checked(session, exit_code, vehicle, action_text, make_session)
        )
        session.start()

    def wifi_checked(self, session: SshSession, exit_code: int, vehicle: Vehicle, action_text: str, make_session) -> None:
        self.command_sessions.remove(session)
        session.deleteLater()
        if exit_code != SUCCESS_EXIT_CODE:
            self.append_output(DEVELOPER_TEXT["wifi_check_failed_text"])
            self.watch_command(vehicle.name, action_text, make_session())
            return
        state = parse_wifi_state(session.lines)
        if state.wifi_connected() and state.has_internet():
            self.append_output(DEVELOPER_TEXT["wifi_ok_text"])
            self.watch_command(vehicle.name, action_text, make_session())
            return
        dialog = WifiDialog(vehicle, state, action_text, self)
        dialog.connected.connect(
            lambda: self.watch_command(vehicle.name, action_text, make_session())
        )
        dialog.exec()

    # Running one command and showing what came back

    def watch_command(
        self, vehicle_name: str, action_text: str, session: SshSession | LocalProcess
    ) -> None:
        """Run one command, put its output in the terminal, say how it ended.

        The session is only started once everything is listening: a Pi that is
        off reports its failure from inside start().
        """
        self.command_sessions.append(session)
        self.append_output(DEVELOPER_TEXT["command_sent"].format(vehicle=vehicle_name, action=action_text))
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
        self, vehicle_name: str, action_text: str, exit_code: int,
        session: SshSession | LocalProcess,
    ) -> None:
        if exit_code == SUCCESS_EXIT_CODE:
            result_text = DEVELOPER_TEXT["command_done"]
        else:
            result_text = DEVELOPER_TEXT["command_failed"]
        self.append_output(result_text.format(vehicle=vehicle_name, action=action_text, exit_code=exit_code))
        self.command_sessions.remove(session)
        session.deleteLater()
