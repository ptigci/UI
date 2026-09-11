"""The map being built on the ground, watched from here.

The ground services stitch the survey frames as they arrive and say how it is
going on the broker; this draws it: how many frames have reached the ground,
whether a build is running, a clock that keeps ticking between messages, the
map itself when it is done and where it was written. OPEN FOLDER opens that
folder on this machine -- the services and this interface normally share the
laptop -- and EXPORT TO USB asks the services to copy the map to the stick
now rather than when the session goes quiet.

The bench half -- pick a folder of recorded frames and stitch it -- is behind
its own switch in general.toml, because it opens a file dialog over the map
and a scored mission never wants that.
"""

from pathlib import Path

from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton

from competitions.suas.config import (
    MAPPING_BENCH_ENABLED,
    MAPPING_BROWSE_TEXT,
    MAPPING_CLOCK_CAPTION,
    MAPPING_CLOCK_FORMAT,
    MAPPING_COMPLETE_FORMAT,
    MAPPING_EXPORT_TEXT,
    MAPPING_EXPORTED_FORMAT,
    MAPPING_FAILED_FORMAT,
    MAPPING_FOLDER_DIALOG_TITLE,
    MAPPING_FRAMES_CAPTION,
    MAPPING_FRAMES_FORMAT,
    MAPPING_NO_FOLDER_TEXT,
    MAPPING_OPEN_FOLDER_TEXT,
    MAPPING_PANEL_TITLE,
    MAPPING_PLACING_FORMAT,
    MAPPING_PREVIEW_MINIMUM_HEIGHT,
    MAPPING_PREVIEW_PLACEHOLDER_TEXT,
    MAPPING_REQUEST_SENT_TEXT,
    MAPPING_RESULTS_FOLDER_IS_LOCAL,
    MAPPING_RUNNING_FORMAT,
    MAPPING_START_TEXT,
    MAPPING_WAITING_TEXT,
)
from theme import flush_layout, set_role, set_state, set_variant
from theme.tokens import (
    ROLE_HINT,
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

# An empty range is how Qt is asked for the busy animation: a bar with no end
# to fill towards, which is what we know while a build is running.
PROGRESS_BUSY_MAXIMUM = 0

SECONDS_PER_MINUTE = 60


class MappingPanel(Card):
    """The live map, its clock, the result, and the way to the file."""

    stitch_requested = pyqtSignal(str)
    export_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent, MAPPING_PANEL_TITLE)

        self.chosen_folder: str = ""
        self.mosaic_path: str = ""

        self.preview_view = CameraView(self)
        self.preview_view.setMinimumHeight(MAPPING_PREVIEW_MINIMUM_HEIGHT)
        self.preview_view.show_placeholder(MAPPING_PREVIEW_PLACEHOLDER_TEXT)

        self.frames_readout = Readout(MAPPING_FRAMES_CAPTION, parent=self)
        self.clock_readout = Readout(MAPPING_CLOCK_CAPTION, parent=self)
        readouts = QHBoxLayout()
        flush_layout(readouts, SPACE_MD)
        readouts.addWidget(self.frames_readout)
        readouts.addWidget(self.clock_readout)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)

        self.status_label = QLabel(MAPPING_WAITING_TEXT, self)
        self.status_label.setWordWrap(True)

        self.open_folder_button = QPushButton(MAPPING_OPEN_FOLDER_TEXT, self)
        set_variant(self.open_folder_button, VARIANT_GHOST)
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.clicked.connect(self.open_results_folder)

        self.export_button = QPushButton(MAPPING_EXPORT_TEXT, self)
        set_variant(self.export_button, VARIANT_PRIMARY)
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_requested.emit)

        buttons = QHBoxLayout()
        flush_layout(buttons, SPACE_MD)
        buttons.addWidget(self.open_folder_button)
        buttons.addWidget(self.export_button)

        self.add_widget(self.preview_view)
        self.add_layout(readouts)
        self.add_widget(self.progress_bar)
        self.add_widget(self.status_label)
        self.add_layout(buttons)

        if MAPPING_BENCH_ENABLED:
            self.build_bench_controls()

        self.show_status(MAPPING_WAITING_TEXT, STATE_NONE)
        self.show_clock(0.0)

    def build_bench_controls(self) -> None:
        """The folder picker and BUILD MAP, for stitching recorded frames."""
        self.folder_label = QLabel(MAPPING_NO_FOLDER_TEXT, self)
        set_role(self.folder_label, ROLE_HINT)
        self.folder_label.setWordWrap(True)

        self.browse_button = QPushButton(MAPPING_BROWSE_TEXT, self)
        set_variant(self.browse_button, VARIANT_GHOST)
        self.browse_button.clicked.connect(self.choose_folder)

        self.start_button = QPushButton(MAPPING_START_TEXT, self)
        set_variant(self.start_button, VARIANT_GHOST)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.request_stitch)

        self.add_widget(self.folder_label)
        self.add_widget(self.browse_button)
        self.add_widget(self.start_button)

    # The operator's side

    def choose_folder(self) -> None:
        """Ask for the folder; a cancelled dialog keeps the last choice."""
        folder = QFileDialog.getExistingDirectory(self, MAPPING_FOLDER_DIALOG_TITLE)
        if not folder:
            return
        self.chosen_folder = folder
        self.folder_label.setText(folder)
        self.start_button.setEnabled(True)

    def request_stitch(self) -> None:
        if not self.chosen_folder:
            return
        self.stitch_requested.emit(self.chosen_folder)

    def show_request_sent(self) -> None:
        self.show_status(MAPPING_REQUEST_SENT_TEXT, STATE_CAUTION)
        self.show_busy_progress()

    def open_results_folder(self) -> None:
        """Open the folder the map was written to, in the desktop's file browser."""
        if not self.mosaic_path or not MAPPING_RESULTS_FOLDER_IS_LOCAL:
            return
        folder = Path(self.mosaic_path).parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    # The ground services' side

    def show_stitch(self, stitch_state, preview) -> None:
        """Draw the ground services' last word on the map.

        Parameters:
            stitch_state (StitchState): What they said.
            preview (QPixmap): The mosaic, null while there is not one.
        """
        self.mosaic_path = stitch_state.mosaic_path
        self.frames_readout.set_value(
            MAPPING_FRAMES_FORMAT.format(received=stitch_state.frames_received,
                                         used=stitch_state.frames_used)
        )
        self.show_clock(stitch_state.elapsed_now())

        if stitch_state.is_running():
            self.show_running(stitch_state)
        elif stitch_state.is_complete():
            self.show_status(
                MAPPING_COMPLETE_FORMAT.format(used=stitch_state.frames_used,
                                               path=stitch_state.mosaic_path),
                STATE_OK,
            )
            self.progress_bar.setVisible(False)
        elif stitch_state.is_exported():
            self.show_status(
                MAPPING_EXPORTED_FORMAT.format(path=stitch_state.export_path),
                STATE_OK,
            )
            self.progress_bar.setVisible(False)
        elif stitch_state.is_failed():
            self.show_status(
                MAPPING_FAILED_FORMAT.format(reason=stitch_state.reason),
                STATE_CRITICAL,
            )
            self.progress_bar.setVisible(False)

        has_map = stitch_state.has_map()
        self.open_folder_button.setEnabled(has_map and MAPPING_RESULTS_FOLDER_IS_LOCAL)
        self.export_button.setEnabled(has_map)

        if not preview.isNull():
            self.preview_view.show_pixmap(preview)

    def refresh_clock(self, stitch_state) -> None:
        """Keep the clock moving between messages while a build runs."""
        if stitch_state.is_running():
            self.show_clock(stitch_state.elapsed_now())

    def show_clock(self, elapsed_seconds: float) -> None:
        minutes, seconds = divmod(int(elapsed_seconds), SECONDS_PER_MINUTE)
        self.clock_readout.set_value(
            MAPPING_CLOCK_FORMAT.format(minutes=minutes, seconds=seconds)
        )

    def show_running(self, stitch_state) -> None:
        """A build that is under way: how far along, in words and in a bar."""
        if not stitch_state.is_counting_frames():
            self.show_status(
                MAPPING_RUNNING_FORMAT.format(received=stitch_state.frames_received,
                                              found=stitch_state.frames_found,
                                              skipped=stitch_state.frames_skipped),
                STATE_CAUTION,
            )
            self.show_busy_progress()
            return

        self.show_status(
            MAPPING_PLACING_FORMAT.format(placed=stitch_state.frames_placed,
                                          to_place=stitch_state.frames_to_place),
            STATE_CAUTION,
        )
        self.progress_bar.setRange(PROGRESS_MINIMUM, stitch_state.frames_to_place)
        self.progress_bar.setValue(stitch_state.frames_placed)
        self.progress_bar.setVisible(True)

    def show_busy_progress(self) -> None:
        """A bar with no end to it, for work whose length nobody has said."""
        self.progress_bar.setRange(PROGRESS_MINIMUM, PROGRESS_BUSY_MAXIMUM)
        self.progress_bar.setVisible(True)

    def show_status(self, status: str, state: str) -> None:
        self.status_label.setText(status)
        self.status_label.setVisible(bool(status))
        set_state(self.status_label, state)
