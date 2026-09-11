"""What runs on this laptop: the ground station, and the vehicles while
SIMULATION is ticked.

A mixin on DevPanel, so these keep using self.monitors, self.pills and
self.output_terminal. A local vehicle's output opens as its monitor, so a
simulation reads like the journals side by side; the ground station writes
into the command output.
"""

from competitions.international_uav.config import DEVELOPER_TEXT
from competitions.international_uav.dev import decode_log_line, local_node_start, set_simulation_mode
from theme.tokens import STATE_IDLE, STATE_OK

SUCCESS_EXIT_CODE = 0


class DevLocalMixin:
    """START GROUND SERVICES, and START/STOP NODES while SIMULATION is ticked."""

    def write_simulation_mode(self) -> bool:
        """Put the SIMULATION box into the config files; False and a line when that failed."""
        try:
            set_simulation_mode(self.simulation_checkbox.isChecked())
        except (OSError, ValueError) as error:
            self.append_output(DEVELOPER_TEXT["simulation_write_failed"].format(reason=error))
            return False
        return True

    # The vehicles in simulation

    def start_local_nodes(self) -> None:
        for vehicle in self.selected_vehicles():
            self.append_output(
                DEVELOPER_TEXT["command_sent"].format(vehicle=vehicle.name, action=DEVELOPER_TEXT["action_start"])
            )
            self.monitors.open_local(vehicle, local_node_start(vehicle, self.monitors))
            self.pills[vehicle.name].show_status(DEVELOPER_TEXT["status_running"], STATE_OK)

    def stop_local_nodes(self, vehicles: list) -> None:
        for vehicle in vehicles:
            if not self.monitors.is_local(vehicle.name):
                continue
            self.monitors.close_local(vehicle.name)
            self.local_node_ended(vehicle.name)
            self.append_output(
                DEVELOPER_TEXT["command_done"].format(vehicle=vehicle.name, action=DEVELOPER_TEXT["action_stop"])
            )

    def local_node_ended(self, vehicle_name: str, exit_code: int = SUCCESS_EXIT_CODE) -> None:
        """The pill says the node is gone; the poll takes it back to the Pi's state."""
        self.pills[vehicle_name].show_status(DEVELOPER_TEXT["status_stopped"], STATE_IDLE)

    # The ground station

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
