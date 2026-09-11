"""What the DEV tab's buttons do: one ssh to the Pi each, reported in the
command output as it goes.

A mixin on DevPanel, so these keep using self.output_terminal and
self.command_sessions. The Pi is asked for its wifi before a pull or a
checkout; without one, the wifi dialog takes over and runs the command itself
once the Pi has a way out. START and STOP go to this laptop instead while
SIMULATION is ticked (dev_local.py).
"""

from PyQt6.QtWidgets import QMessageBox

from competitions.suas.config import DEVELOPER_TEXT
from competitions.suas.dev import (
    LocalProcess,
    SshSession,
    connectivity_check,
    parse_connectivity,
    repository_checkout,
    repository_pull,
    repository_push,
    repository_restore,
    vtol_reboot,
    vtol_start,
    vtol_stop,
)
from competitions.suas.widgets.wifi_dialog import WifiDialog

SUCCESS_EXIT_CODE = 0


class DevCommandsMixin:
    """The START, STOP, REBOOT, PULL, PUSH, CHECKOUT and RESTORE buttons."""

    def confirmed(self, title: str, question: str) -> bool:
        """Whether the operator said yes to the question."""
        answer = QMessageBox.question(
            self, title, question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    # The buttons

    def start_vtol(self) -> None:
        """The Pi, or this laptop while SIMULATION is ticked.

        The Pi does not read the local config file, so a switch that could not
        be written only stops a local start.
        """
        switch_written = self.write_simulation_mode()
        if self.simulation_checkbox.isChecked():
            if switch_written:
                self.start_local_vtol()
            return
        self.watch_command(DEVELOPER_TEXT["action_start"], vtol_start(self))

    def stop_vtol(self) -> None:
        """A node started here stops whatever the box says; the Pi only when it is off."""
        self.stop_local_vtol()
        if self.simulation_checkbox.isChecked():
            return
        self.watch_command(DEVELOPER_TEXT["action_stop"], vtol_stop(self))

    def reboot_pi(self) -> None:
        """Reboot the Pi itself, once the operator has said so twice."""
        if not self.confirmed(DEVELOPER_TEXT["reboot_title"], DEVELOPER_TEXT["reboot_question"]):
            return
        self.watch_command(DEVELOPER_TEXT["action_reboot"], vtol_reboot(self))

    def restore_repository(self) -> None:
        """Throw away the edits on the Pi, once the operator has said so twice."""
        if not self.confirmed(DEVELOPER_TEXT["restore_title"], DEVELOPER_TEXT["restore_question"]):
            return
        self.watch_command(DEVELOPER_TEXT["action_restore"], repository_restore(self))

    def pull_repository(self) -> None:
        self.run_with_wifi(DEVELOPER_TEXT["action_pull"], lambda: repository_pull(self))

    def push_repository(self) -> None:
        """Send the branch open here to the Pi, for a board with no internet.

        The one button here that runs on this laptop rather than on the Pi:
        the commits are here, so it is a git here that sends them over. It
        also skips the wifi check, because a push needs nothing but ssh.
        """
        self.watch_command(DEVELOPER_TEXT["action_push"], repository_push(self))

    def checkout_branch(self) -> None:
        branch = self.branch_input.text().strip()
        if not branch:
            self.append_output(DEVELOPER_TEXT["no_branch_text"])
            return
        action_text = DEVELOPER_TEXT["action_checkout"].format(branch=branch)
        self.run_with_wifi(action_text, lambda: repository_checkout(branch, self))

    # The Pi's wifi, before anything that needs the internet

    def run_with_wifi(self, action_text: str, make_session) -> None:
        self.append_output(DEVELOPER_TEXT["wifi_checking_text"].format(action=action_text))
        session = connectivity_check(self)
        self.command_sessions.append(session)
        session.finished.connect(
            lambda exit_code: self.wifi_checked(session, exit_code, action_text, make_session)
        )
        session.start()

    def wifi_checked(self, session: SshSession, exit_code: int, action_text: str, make_session) -> None:
        self.command_sessions.remove(session)
        session.deleteLater()
        if exit_code != SUCCESS_EXIT_CODE:
            self.append_output(DEVELOPER_TEXT["wifi_check_failed_text"])
            self.watch_command(action_text, make_session())
            return
        state = parse_connectivity(session.lines)
        if state.wifi_connected() and state.has_internet():
            self.append_output(DEVELOPER_TEXT["wifi_ok_text"])
            self.watch_command(action_text, make_session())
            return
        dialog = WifiDialog(state, action_text, self)
        dialog.connected.connect(lambda: self.watch_command(action_text, make_session()))
        dialog.exec()

    # Running one command and showing what came back

    def watch_command(self, action_text: str, session: SshSession | LocalProcess) -> None:
        """Run one command, put its output in the terminal, say how it ended.

        The session is only started once everything is listening: a Pi that is
        off reports its failure from inside start().
        """
        self.command_sessions.append(session)
        self.append_output(DEVELOPER_TEXT["command_sent"].format(
            vehicle=DEVELOPER_TEXT["vtol_name"], action=action_text
        ))
        session.line_received.connect(
            lambda line: self.append_output(
                DEVELOPER_TEXT["output_line"].format(vehicle=DEVELOPER_TEXT["vtol_name"], line=line)
            )
        )
        session.finished.connect(
            lambda exit_code: self.report_command(action_text, exit_code, session)
        )
        session.start()

    def report_command(
        self, action_text: str, exit_code: int, session: SshSession | LocalProcess
    ) -> None:
        if exit_code == SUCCESS_EXIT_CODE:
            result_text = DEVELOPER_TEXT["command_done"]
        else:
            result_text = DEVELOPER_TEXT["command_failed"]
        self.append_output(result_text.format(
            vehicle=DEVELOPER_TEXT["vtol_name"], action=action_text, exit_code=exit_code
        ))
        self.command_sessions.remove(session)
        session.deleteLater()
