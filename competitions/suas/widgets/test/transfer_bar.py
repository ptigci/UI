"""The copy off the camera's card, along the bottom of the page.

A 4K still is several megabytes and the link it comes down is the same 2.4 GHz
that carries the video, so a fetch is slow enough that the operator needs to see
it moving. The bar is the honest version of that: it fills against the bytes the
aircraft says it is sending, and when the aircraft has not said how much there
is — a watch that copies frames as they are taken never knows — it spins instead
of sitting empty at nought per cent.

The two send toggles follow the aircraft's word rather than the click, the same
way the record button does. A button that says STOP because somebody pressed
START is a button that stops something that never began.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton

from competitions.suas.config import (
    CAMERA_TEST_ACTIONS,
    MISSING_VALUE_TEXT,
    TEST_CAMERA_TEXT,
    TEST_LAYOUT,
    TEST_TRANSFER_TEXT,
)
from theme import flush_layout, set_role, set_state, set_variant
from theme.tokens import (
    ROLE_HINT,
    SPACE_MD,
    STATE_CAUTION,
    STATE_CRITICAL,
    STATE_NONE,
    STATE_OK,
    VARIANT_CAUTION,
    VARIANT_GHOST,
)
from widgets import Card, Readout

SEND_PHOTOS_ON_ACTION = CAMERA_TEST_ACTIONS["send_photos_on"]
SEND_PHOTOS_OFF_ACTION = CAMERA_TEST_ACTIONS["send_photos_off"]
SEND_VIDEOS_ON_ACTION = CAMERA_TEST_ACTIONS["send_videos_on"]
SEND_VIDEOS_OFF_ACTION = CAMERA_TEST_ACTIONS["send_videos_off"]

PROGRESS_MINIMUM = 0

# An empty range is how Qt is asked for the busy animation: a bar with no end to
# fill towards, which is all we know until the aircraft says how much there is.
PROGRESS_BUSY_MAXIMUM = 0


class TransferBar(Card):
    """What is being copied here, how far through it is, and where it lands."""

    send_toggled = pyqtSignal(str)
    open_folder_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent, TEST_TRANSFER_TEXT["title"])

        self.sending_photos = False
        self.sending_videos = False

        self.photos_button = QPushButton(self)
        self.photos_button.clicked.connect(self.request_photos)
        self.videos_button = QPushButton(self)
        self.videos_button.clicked.connect(self.request_videos)

        toggles = QHBoxLayout()
        flush_layout(toggles, SPACE_MD)
        toggles.addWidget(self.photos_button)
        toggles.addWidget(self.videos_button)

        self.files_reading = Readout(TEST_TRANSFER_TEXT["files_caption"], parent=self)

        self.bytes_label = QLabel(self)
        set_role(self.bytes_label, ROLE_HINT)

        counts = QHBoxLayout()
        flush_layout(counts, SPACE_MD)
        counts.addWidget(self.files_reading)
        counts.addWidget(self.bytes_label)
        counts.addStretch()

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimumHeight(TEST_LAYOUT["progress_bar_height"])
        self.progress_bar.setVisible(False)

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)

        self.folder_reading = Readout(TEST_TRANSFER_TEXT["saved_caption"], parent=self)
        self.folder_reading.set_value(TEST_TRANSFER_TEXT["download_folder"])

        self.open_folder_button = QPushButton(TEST_TRANSFER_TEXT["open_folder_text"],
                                              self)
        set_variant(self.open_folder_button, VARIANT_GHOST)
        self.open_folder_button.clicked.connect(self.open_folder_requested.emit)

        folder_row = QHBoxLayout()
        flush_layout(folder_row, SPACE_MD)
        folder_row.addWidget(self.folder_reading)
        folder_row.addWidget(self.open_folder_button)
        folder_row.addStretch()

        self.add_layout(toggles)
        self.add_layout(counts)
        self.add_widget(self.progress_bar)
        self.add_widget(self.status_label)
        self.add_layout(folder_row)

        self.show_sending(False, False)
        self.clear_counts()
        self.show_status(TEST_TRANSFER_TEXT["idle_text"], STATE_NONE)

    # The operator's side

    def request_photos(self) -> None:
        if self.sending_photos:
            self.send_toggled.emit(SEND_PHOTOS_OFF_ACTION)
            return
        self.send_toggled.emit(SEND_PHOTOS_ON_ACTION)

    def request_videos(self) -> None:
        if self.sending_videos:
            self.send_toggled.emit(SEND_VIDEOS_OFF_ACTION)
            return
        self.send_toggled.emit(SEND_VIDEOS_ON_ACTION)

    # The aircraft's side

    def show_transfer(self, media_state) -> None:
        """Draw the aircraft's last word on the copy."""
        self.show_sending(media_state.sending_photos, media_state.sending_videos)

        if media_state.is_listing():
            self.clear_counts()
            self.show_busy_progress()
            self.show_status(TEST_TRANSFER_TEXT["listing_text"], STATE_CAUTION)
            return

        if media_state.is_fetching():
            self.show_fetching(media_state)
            return

        self.clear_counts()
        self.progress_bar.setVisible(False)

        if media_state.is_complete():
            self.show_status(
                TEST_TRANSFER_TEXT["complete_format"].format(
                    files_done=media_state.files_done),
                STATE_OK,
            )
            return

        if media_state.is_failed():
            self.show_status(
                TEST_TRANSFER_TEXT["failed_format"].format(
                    reason=media_state.transfer_reason),
                STATE_CRITICAL,
            )
            return

        self.show_status(TEST_TRANSFER_TEXT["idle_text"], STATE_NONE)

    def show_fetching(self, media_state) -> None:
        """A copy under way: which file, how many, and how many megabytes in."""
        self.files_reading.set_value(
            TEST_TRANSFER_TEXT["fetching_format"].format(
                file_name=media_state.file_name,
                files_done=media_state.files_done,
                files_total=media_state.files_total,
            )
        )
        self.show_status("", STATE_NONE)

        if not media_state.knows_the_size():
            self.bytes_label.setText("")
            self.show_busy_progress()
            return

        self.bytes_label.setText(
            TEST_TRANSFER_TEXT["bytes_format"].format(
                done=media_state.megabytes_done(),
                total=media_state.megabytes_total(),
            )
        )
        self.progress_bar.setRange(PROGRESS_MINIMUM, media_state.bytes_total)
        self.progress_bar.setValue(media_state.bytes_done)
        self.progress_bar.setVisible(True)

    def show_sending(self, sending_photos: bool, sending_videos: bool) -> None:
        """Follow the aircraft's word on the two send toggles."""
        self.sending_photos = sending_photos
        self.sending_videos = sending_videos
        self.show_toggle(self.photos_button, sending_photos,
                         TEST_CAMERA_TEXT["send_photos_on_text"],
                         TEST_CAMERA_TEXT["send_photos_off_text"])
        self.show_toggle(self.videos_button, sending_videos,
                         TEST_CAMERA_TEXT["send_videos_on_text"],
                         TEST_CAMERA_TEXT["send_videos_off_text"])

    def show_toggle(self, button, sending: bool, on_text: str, off_text: str) -> None:
        if sending:
            button.setText(off_text)
            set_variant(button, VARIANT_CAUTION)
            return
        button.setText(on_text)
        set_variant(button, VARIANT_GHOST)

    def show_busy_progress(self) -> None:
        """A bar with no end to it, for a copy whose length nobody has said."""
        self.progress_bar.setRange(PROGRESS_MINIMUM, PROGRESS_BUSY_MAXIMUM)
        self.progress_bar.setVisible(True)

    def clear_counts(self) -> None:
        self.files_reading.set_value(MISSING_VALUE_TEXT)
        self.bytes_label.setText("")

    # What the aircraft made of the last toggle
    #
    # These share the line the transfer itself writes on, so the next message
    # from the aircraft replaces them. That is the right way round -- what the
    # copy is actually doing beats what the last press was told -- and the
    # refusal is in the camera test's log either way.

    def show_command_sent(self) -> None:
        self.show_status(TEST_CAMERA_TEXT["command_sent_text"], STATE_CAUTION)

    def show_command_accepted(self) -> None:
        self.show_status("", STATE_OK)

    def show_command_rejected(self, reason: str) -> None:
        self.show_status(
            TEST_CAMERA_TEXT["command_rejected_format"].format(reason=reason),
            STATE_CRITICAL,
        )

    def show_command_timeout(self) -> None:
        self.show_status(TEST_CAMERA_TEXT["command_timeout_text"], STATE_CRITICAL)

    def show_status(self, status: str, state: str) -> None:
        self.status_label.setText(status)
        self.status_label.setVisible(bool(status))
        set_state(self.status_label, state)
