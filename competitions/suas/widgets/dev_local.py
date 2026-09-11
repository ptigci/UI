"""What runs on this laptop: the ground services, the vtol node while
SIMULATION is ticked, and the test mission that flies it.

A mixin on DevPanel, so these keep using self.local_vtol, self.unit_pill,
the monitor terminal and self.output_terminal. The local vtol node's output
goes into the monitor, where the journal would be; the ground services and the
test mission write into the command output.
"""

from competitions.suas.config import DEVELOPER_TEXT
from competitions.suas.dev import (
    LocalProcess,
    decode_log_line,
    set_simulation_mode,
    test_mission_start,
    vtol_start_local,
)
from theme.tokens import STATE_IDLE, STATE_OK

SUCCESS_EXIT_CODE = 0


class DevLocalMixin:
    """START GROUND SERVICES, START/STOP VTOL and TEST MISSION, all on this laptop."""

    def write_simulation_mode(self) -> bool:
        """Put the SIMULATION box into the config file; False and a line when that failed."""
        try:
            set_simulation_mode(self.simulation_checkbox.isChecked())
        except (OSError, ValueError) as error:
            self.append_output(DEVELOPER_TEXT["simulation_write_failed"].format(reason=error))
            return False
        return True

    # The vtol node in simulation

    def start_local_vtol(self) -> None:
        """Run the node here; an older run of it is stopped first."""
        self.stop_local_vtol()
        node = vtol_start_local(self)
        self.local_vtol = node
        node.line_received.connect(self.show_monitor_line)
        node.finished.connect(lambda exit_code: self.local_vtol_ended(node, exit_code))
        self.append_output(DEVELOPER_TEXT["command_sent"].format(
            vehicle=DEVELOPER_TEXT["vtol_name"], action=DEVELOPER_TEXT["action_start"]
        ))
        node.start()
        self.unit_pill.show_status(DEVELOPER_TEXT["status_running"], STATE_OK)

    def stop_local_vtol(self) -> None:
        if self.local_vtol is None:
            return
        node = self.local_vtol
        self.local_vtol = None
        node.stop()
        node.deleteLater()
        self.unit_pill.show_status(DEVELOPER_TEXT["status_stopped"], STATE_IDLE)
        self.append_output(DEVELOPER_TEXT["command_done"].format(
            vehicle=DEVELOPER_TEXT["vtol_name"], action=DEVELOPER_TEXT["action_stop"]
        ))

    def local_vtol_ended(self, node: LocalProcess, exit_code: int) -> None:
        """The node stopped on its own; the poll takes the pill back to the Pi's state."""
        if node is not self.local_vtol:
            return  # stopped from the button, which reports it itself
        self.local_vtol = None
        node.deleteLater()
        self.unit_pill.show_status(DEVELOPER_TEXT["status_stopped"], STATE_IDLE)
        self.append_output(DEVELOPER_TEXT["local_node_ended"].format(
            vehicle=DEVELOPER_TEXT["vtol_name"], exit_code=exit_code
        ))

    # The test mission

    def run_test_mission(self) -> None:
        """Do the operator's job against SITL: upload, arm, start AUTO.

        It runs once and ends, so there is nothing to stop and no pill: what
        happened is in the output, item by item.
        """
        if self.test_mission is not None:
            return  # one at a time; the button says so by staying disabled
        mission = test_mission_start(self)
        self.test_mission = mission
        mission.line_received.connect(self.show_test_mission_line)
        mission.finished.connect(self.test_mission_finished)
        self.append_output(DEVELOPER_TEXT["command_sent"].format(
            vehicle=DEVELOPER_TEXT["test_mission_name"],
            action=DEVELOPER_TEXT["action_test_mission"],
        ))
        self.refresh_test_mission_button()
        mission.start()

    def show_test_mission_line(self, line: str) -> None:
        self.append_output(DEVELOPER_TEXT["output_line"].format(
            vehicle=DEVELOPER_TEXT["test_mission_name"], line=line
        ))

    def test_mission_finished(self, exit_code: int) -> None:
        mission = self.test_mission
        self.test_mission = None
        mission.deleteLater()
        if exit_code == SUCCESS_EXIT_CODE:
            result_text = DEVELOPER_TEXT["command_done"]
        else:
            result_text = DEVELOPER_TEXT["command_failed"]
        self.append_output(result_text.format(
            vehicle=DEVELOPER_TEXT["test_mission_name"],
            action=DEVELOPER_TEXT["action_test_mission"], exit_code=exit_code,
        ))
        self.refresh_test_mission_button()

    def stop_test_mission(self) -> None:
        """Kill a mission upload still in flight, before the tab goes away."""
        if self.test_mission is None:
            return
        mission = self.test_mission
        self.test_mission = None
        mission.stop()
        mission.deleteLater()

    # The ground services

    def toggle_ground(self) -> None:
        if self.ground.is_running():
            self.ground.stop()
            return
        if not self.write_simulation_mode():
            return
        self.append_output(DEVELOPER_TEXT["command_sent"].format(
            vehicle=DEVELOPER_TEXT["ground_name"], action=DEVELOPER_TEXT["action_ground"]
        ))
        self.ground.start()
        self.ground_button.setText(DEVELOPER_TEXT["ground_stop_text"])
        self.ground_pill.show_status(DEVELOPER_TEXT["status_running"], STATE_OK)

    def show_ground_line(self, line: str) -> None:
        """The node logs in colour; the codes come off before the line joins the output."""
        text, log_state = decode_log_line(line)
        self.append_output(
            DEVELOPER_TEXT["output_line"].format(vehicle=DEVELOPER_TEXT["ground_name"], line=text)
        )

    def ground_finished(self, exit_code: int) -> None:
        if exit_code == SUCCESS_EXIT_CODE:
            result_text = DEVELOPER_TEXT["command_done"]
        else:
            result_text = DEVELOPER_TEXT["command_failed"]
        self.append_output(result_text.format(
            vehicle=DEVELOPER_TEXT["ground_name"], action=DEVELOPER_TEXT["action_ground"], exit_code=exit_code
        ))
        self.ground_button.setText(DEVELOPER_TEXT["ground_start_text"])
        self.ground_pill.show_status(DEVELOPER_TEXT["status_stopped"], STATE_IDLE)
