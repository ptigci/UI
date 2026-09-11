"""Two mapping tests on one page, because they prove different things.

IN THE AIR is the flight. Switched on, the aircraft starts taking mapping frames
and sending them down with the position and the yaw, pitch and roll they were
taken at. Switched off, it stops, the ground services stitch what arrived, and
the mosaic comes back and is saved on their disk. Nobody on this end ever knows
the folder they filled, which is why that stitch is asked for with no path.

FROM A FOLDER is the bench. Point the ground services at a folder of frames from
a flight that has already happened and stitch it again. It is the only way to
work on the stitcher without flying.

The three counts under the toggle are separate on purpose. A capture taking
frames while `sent` sits still is a link problem, not a camera problem, and
seeing that before the flight ends is worth the room they take. The toggle's own
label follows the aircraft rather than the click, so a press the aircraft never
took does not leave the button claiming otherwise.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton

from competitions.suas.config import (
    MAPPING_ACTIONS,
    MAPPING_CLOCK_CAPTION,
    MAPPING_CLOCK_FORMAT,
    MAPPING_EXPORTED_FORMAT,
    MAPPING_FAILED_FORMAT,
    MAPPING_FRAMES_CAPTION,
    MAPPING_FRAMES_FORMAT,
    MAPPING_PLACING_FORMAT,
    MAPPING_PREVIEW_MINIMUM_HEIGHT,
    MAPPING_RUNNING_FORMAT,
    TEST_MAPPING_TEXT,
)
from theme import flush_layout, set_role, set_state, set_variant
from theme.tokens import (
    ROLE_HINT,
    ROLE_SUBHEADING,
    SPACE_MD,
    STATE_CAUTION,
    STATE_CRITICAL,
    STATE_NONE,
    STATE_OK,
    VARIANT_GHOST,
    VARIANT_PRIMARY,
)
from widgets import Card, CameraView, Readout

PROGRESS_MINIMUM = 0

# An empty range is how Qt is asked for the busy animation: a bar with no end to
# fill towards, which is what we know while a build is running.
PROGRESS_BUSY_MAXIMUM = 0

SECONDS_PER_MINUTE = 60

# The stitch that follows STOP has no path: the ground services stitch the
# session they have just been filling.
LIVE_SESSION = ""


class MappingTestPanel(Card):
    """The capture toggle, the folder stitch, and the map both of them make."""

    capture_toggled = pyqtSignal(str)
    stitch_requested = pyqtSignal(str)
    open_folder_requested = pyqtSignal()
    export_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent, TEST_MAPPING_TEXT["title"])

        self.capturing = False
        self.chosen_folder: str = ""

        self.capture_button = QPushButton(TEST_MAPPING_TEXT["start_capture_text"], self)
        set_variant(self.capture_button, VARIANT_PRIMARY)
        self.capture_button.clicked.connect(self.toggle_capture)

        self.capture_label = QLabel(TEST_MAPPING_TEXT["capture_idle_text"], self)
        self.capture_label.setWordWrap(True)

        self.add_widget(self.build_heading(TEST_MAPPING_TEXT["capture_title"]))
        self.add_widget(self.capture_button)
        self.add_widget(self.capture_label)

        self.browse_button = QPushButton(TEST_MAPPING_TEXT["browse_text"], self)
        set_variant(self.browse_button, VARIANT_GHOST)
        self.browse_button.clicked.connect(self.choose_folder)

        self.folder_label = QLabel(TEST_MAPPING_TEXT["no_folder_text"], self)
        set_role(self.folder_label, ROLE_HINT)
        self.folder_label.setWordWrap(True)

        self.build_button = QPushButton(TEST_MAPPING_TEXT["build_text"], self)
        set_variant(self.build_button, VARIANT_GHOST)
        self.build_button.setEnabled(False)
        self.build_button.clicked.connect(self.request_folder_stitch)

        self.add_widget(self.build_heading(TEST_MAPPING_TEXT["bench_title"]))
        self.add_widget(self.browse_button)
        self.add_widget(self.folder_label)
        self.add_widget(self.build_button)

        self.preview_view = CameraView(self)
        self.preview_view.setMinimumHeight(MAPPING_PREVIEW_MINIMUM_HEIGHT)
        self.preview_view.show_placeholder(TEST_MAPPING_TEXT["preview_placeholder_text"])

        self.frames_readout = Readout(MAPPING_FRAMES_CAPTION, parent=self)
        self.clock_readout = Readout(MAPPING_CLOCK_CAPTION, parent=self)
        readouts = QHBoxLayout()
        flush_layout(readouts, SPACE_MD)
        readouts.addWidget(self.frames_readout)
        readouts.addWidget(self.clock_readout)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)

        self.stitch_label = QLabel(self)
        self.stitch_label.setWordWrap(True)

        self.saved_label = QLabel(self)
        set_role(self.saved_label, ROLE_HINT)
        self.saved_label.setWordWrap(True)

        self.open_folder_button = QPushButton(TEST_MAPPING_TEXT["open_folder_text"], self)
        set_variant(self.open_folder_button, VARIANT_GHOST)
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.clicked.connect(self.open_folder_requested.emit)

        self.export_button = QPushButton(TEST_MAPPING_TEXT["export_text"], self)
        set_variant(self.export_button, VARIANT_PRIMARY)
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_requested.emit)

        map_buttons = QHBoxLayout()
        flush_layout(map_buttons, SPACE_MD)
        map_buttons.addWidget(self.open_folder_button)
        map_buttons.addWidget(self.export_button)

        self.add_widget(self.preview_view)
        self.add_layout(readouts)
        self.add_widget(self.progress_bar)
        self.add_widget(self.stitch_label)
        self.add_widget(self.saved_label)
        self.add_layout(map_buttons)

        self.show_clock(0.0)
        self.show_stitch_status("", STATE_NONE)
        self.show_saved("")

    def build_heading(self, title: str) -> QLabel:
        heading_label = QLabel(title, self)
        set_role(heading_label, ROLE_SUBHEADING)
        return heading_label

    # The operator's side

    def toggle_capture(self) -> None:
        """Stopping is two messages: the aircraft stops, the ground stitches."""
        if self.capturing:
            self.capture_toggled.emit(MAPPING_ACTIONS["stop_capture"])
            self.stitch_requested.emit(LIVE_SESSION)
            return
        self.capture_toggled.emit(MAPPING_ACTIONS["start_capture"])

    def choose_folder(self) -> None:
        """Ask for the folder; a cancelled dialog keeps the last choice."""
        folder = QFileDialog.getExistingDirectory(
            self, TEST_MAPPING_TEXT["folder_dialog_title"])
        if not folder:
            return
        self.chosen_folder = folder
        self.folder_label.setText(folder)
        self.build_button.setEnabled(True)

    def request_folder_stitch(self) -> None:
        if not self.chosen_folder:
            return
        self.stitch_requested.emit(self.chosen_folder)

    # What the aircraft says about the capture

    def show_capture(self, mapping_capture_state) -> None:
        self.capturing = mapping_capture_state.capturing
        if self.capturing:
            self.capture_button.setText(TEST_MAPPING_TEXT["stop_capture_text"])
        else:
            self.capture_button.setText(TEST_MAPPING_TEXT["start_capture_text"])

        if not self.capturing:
            self.show_capture_status(TEST_MAPPING_TEXT["capture_idle_text"], STATE_NONE)
            return

        if not mapping_capture_state.is_live():
            self.show_capture_status(TEST_MAPPING_TEXT["capture_stale_text"],
                                     STATE_CRITICAL)
            return

        self.show_capture_status(
            TEST_MAPPING_TEXT["capture_running_format"].format(
                captured=mapping_capture_state.frames_captured,
                sent=mapping_capture_state.frames_sent,
                queued=mapping_capture_state.frames_queued,
            ),
            STATE_CAUTION,
        )

    def show_capture_status(self, status: str, state: str) -> None:
        self.capture_label.setText(status)
        set_state(self.capture_label, state)

    # What the ground services say about the map

    def show_stitch(self, stitch_state, preview_pixmap) -> None:
        """Draw the ground services' last word on the map.

        Parameters:
            stitch_state (StitchState): What they said.
            preview_pixmap (QPixmap): The mosaic, null while there is not one.
        """
        self.frames_readout.set_value(
            MAPPING_FRAMES_FORMAT.format(received=stitch_state.frames_received,
                                         used=stitch_state.frames_used)
        )
        self.show_clock(stitch_state.elapsed_now())

        if stitch_state.is_running():
            self.show_running(stitch_state)
        elif stitch_state.is_complete():
            self.finish_stitch(
                TEST_MAPPING_TEXT["built_format"].format(used=stitch_state.frames_used),
                STATE_OK,
            )
        elif stitch_state.is_exported():
            self.finish_stitch(
                MAPPING_EXPORTED_FORMAT.format(path=stitch_state.export_path), STATE_OK
            )
        elif stitch_state.is_failed():
            self.finish_stitch(
                MAPPING_FAILED_FORMAT.format(reason=stitch_state.reason), STATE_CRITICAL
            )

        self.show_saved(stitch_state.mosaic_path)
        self.open_folder_button.setEnabled(stitch_state.has_map())
        self.export_button.setEnabled(stitch_state.has_map())

        if not preview_pixmap.isNull():
            self.preview_view.show_pixmap(preview_pixmap)

    def show_running(self, stitch_state) -> None:
        """A build under way: how far along, in words and in a bar."""
        if not stitch_state.is_counting_frames():
            self.show_stitch_status(
                MAPPING_RUNNING_FORMAT.format(received=stitch_state.frames_received,
                                              found=stitch_state.frames_found,
                                              skipped=stitch_state.frames_skipped),
                STATE_CAUTION,
            )
            self.progress_bar.setRange(PROGRESS_MINIMUM, PROGRESS_BUSY_MAXIMUM)
            self.progress_bar.setVisible(True)
            return

        self.show_stitch_status(
            MAPPING_PLACING_FORMAT.format(placed=stitch_state.frames_placed,
                                          to_place=stitch_state.frames_to_place),
            STATE_CAUTION,
        )
        self.progress_bar.setRange(PROGRESS_MINIMUM, stitch_state.frames_to_place)
        self.progress_bar.setValue(stitch_state.frames_placed)
        self.progress_bar.setVisible(True)

    def finish_stitch(self, status: str, state: str) -> None:
        self.show_stitch_status(status, state)
        self.progress_bar.setVisible(False)

    def refresh_clock(self, stitch_state) -> None:
        """Keep the clock moving between messages while a build runs."""
        if stitch_state.is_running():
            self.show_clock(stitch_state.elapsed_now())

    def show_clock(self, elapsed_seconds: float) -> None:
        minutes, seconds = divmod(int(elapsed_seconds), SECONDS_PER_MINUTE)
        self.clock_readout.set_value(
            MAPPING_CLOCK_FORMAT.format(minutes=minutes, seconds=seconds)
        )

    def show_saved(self, mosaic_path: str) -> None:
        self.saved_label.setText(
            TEST_MAPPING_TEXT["saved_format"].format(path=mosaic_path)
        )
        self.saved_label.setVisible(bool(mosaic_path))

    def show_stitch_status(self, status: str, state: str) -> None:
        self.stitch_label.setText(status)
        self.stitch_label.setVisible(bool(status))
        set_state(self.stitch_label, state)

    # What the operator's last press came to

    def show_command_sent(self) -> None:
        self.show_capture_status(TEST_MAPPING_TEXT["capture_sent_text"], STATE_CAUTION)

    def show_command_accepted(self) -> None:
        self.show_capture_status(TEST_MAPPING_TEXT["capture_accepted_text"], STATE_OK)

    def show_command_rejected(self, reason: str) -> None:
        self.show_capture_status(
            TEST_MAPPING_TEXT["capture_rejected_format"].format(reason=reason),
            STATE_CRITICAL,
        )

    def show_command_timeout(self) -> None:
        self.show_capture_status(TEST_MAPPING_TEXT["capture_timeout_text"],
                                 STATE_CRITICAL)
