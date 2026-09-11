"""What runs on this laptop: the computer node, and the drone nodes while
SIMULATION is ticked.

A mixin on DevPanel, so these keep using self.local_nodes, the monitor cards
and self.output_terminal. A local drone node's output opens as its monitor,
so a simulation reads like three journals side by side; the computer node
writes into the command output like the ground station of the other tabs.
"""

from competitions.swarm_uav.config import DEVELOPER_TEXT
from competitions.swarm_uav.dev import decode_log_line, node_start_local, set_simulation_mode
from theme.tokens import STATE_IDLE, STATE_OK

SUCCESS_EXIT_CODE = 0


class DevLocalMixin:
    """START COMPUTER NODE, and START/STOP NODES while SIMULATION is ticked."""

    def write_simulation_mode(self) -> bool:
        """Put the SIMULATION box into the config files; False and a line when that failed."""
        try:
            set_simulation_mode(self.simulation_checkbox.isChecked())
        except (OSError, ValueError) as error:
            self.append_output(DEVELOPER_TEXT["simulation_write_failed"].format(reason=error))
            return False
        return True

    # The drone nodes in simulation

    def start_local_nodes(self) -> None:
        for vehicle_id, vehicle_name in self.selected_drones():
            # A journal or an older run of the same drone gives its card up.
            if vehicle_id in self.monitor_cards:
                self.close_monitor(vehicle_id)
            node = node_start_local(vehicle_id, self)
            self.local_nodes[vehicle_id] = node
            self.open_monitor(vehicle_id, vehicle_name, node)
            self.append_output(
                DEVELOPER_TEXT["command_sent"].format(
                    vehicle=vehicle_name, action=DEVELOPER_TEXT["action_start"]
                )
            )
            node.start()
        self.layout_monitors()

    def stop_local_nodes(self, drones: list[tuple[int, str]]) -> None:
        for vehicle_id, vehicle_name in drones:
            if vehicle_id not in self.local_nodes:
                continue
            self.close_monitor(vehicle_id)
            self.append_output(
                DEVELOPER_TEXT["command_done"].format(
                    vehicle=vehicle_name, action=DEVELOPER_TEXT["action_stop"]
                )
            )
        self.layout_monitors()

    # The computer node

    def toggle_computer(self) -> None:
        """One button: it starts the node, and once it runs it stops it."""
        if self.computer.is_running():
            self.computer.stop()
            return
        if not self.write_simulation_mode():
            return
        self.append_output(
            DEVELOPER_TEXT["command_sent"].format(
                vehicle=DEVELOPER_TEXT["computer_name"], action=DEVELOPER_TEXT["action_computer"]
            )
        )
        self.computer.start()
        self.computer_button.setText(DEVELOPER_TEXT["computer_stop_text"])
        self.computer_pill.show_status(DEVELOPER_TEXT["status_running"], STATE_OK)

    def show_computer_line(self, line: str) -> None:
        """The node logs in colour; the codes come off before the line joins the output."""
        text, log_state = decode_log_line(line)
        self.append_output(
            DEVELOPER_TEXT["output_line"].format(vehicle=DEVELOPER_TEXT["computer_name"], line=text)
        )

    def computer_finished(self, exit_code: int) -> None:
        if exit_code == SUCCESS_EXIT_CODE:
            result_text = DEVELOPER_TEXT["command_done"]
        else:
            result_text = DEVELOPER_TEXT["command_failed"]
        self.append_output(
            result_text.format(
                vehicle=DEVELOPER_TEXT["computer_name"],
                action=DEVELOPER_TEXT["action_computer"],
                exit_code=exit_code,
            )
        )
        self.computer_button.setText(DEVELOPER_TEXT["computer_start_text"])
        self.computer_pill.show_status(DEVELOPER_TEXT["status_stopped"], STATE_IDLE)
