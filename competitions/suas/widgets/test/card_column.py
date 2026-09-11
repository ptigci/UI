"""The presses that act on the camera's own microSD card, down the left.

The A8 mini writes 4K to the card in its body and nothing else ever does. The
Ethernet stream the Pi reads stops at 1080p, so a full-resolution frame exists
in exactly one place and the only way to see it is to ask the camera for the
file. That is what this column is: the same four presses as the stream side,
aimed at the other card, plus the listing and the fetch that bring a file here.

GET FRAMES CONSTANTLY is a toggle, and its label follows the aircraft rather
than the click — the same reasoning as the record button on the mission screen.
A button that says STOP because somebody pressed START is a button that stops
something that never began.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
)

from competitions.suas.config import (
    CAMERA_TEST_ACTIONS,
    TEST_CAMERA_TEXT,
    TEST_CARD_TEXT,
    TEST_LAYOUT,
)
from theme import flush_layout, set_role, set_state, set_variant
from theme.tokens import (
    ROLE_HINT,
    ROLE_READOUT_LABEL,
    ROLE_SUBHEADING,
    SPACE_SM,
    STATE_CAUTION,
    STATE_CRITICAL,
    STATE_NONE,
    STATE_OK,
    VARIANT_CAUTION,
    VARIANT_GHOST,
)
from widgets import Card

START_VIDEO_ACTION = CAMERA_TEST_ACTIONS["card_start_video"]
STOP_VIDEO_ACTION = CAMERA_TEST_ACTIONS["card_stop_video"]
TAKE_PHOTO_ACTION = CAMERA_TEST_ACTIONS["card_take_photo"]
START_TIMER_ACTION = CAMERA_TEST_ACTIONS["card_start_photo_timer"]
STOP_TIMER_ACTION = CAMERA_TEST_ACTIONS["card_stop_photo_timer"]
LIST_FILES_ACTION = CAMERA_TEST_ACTIONS["card_list_files"]
WATCH_ON_ACTION = CAMERA_TEST_ACTIONS["card_watch_on"]
WATCH_OFF_ACTION = CAMERA_TEST_ACTIONS["card_watch_off"]


class CardColumn(Card):
    """Four presses on the camera's card, the listing, and the way to fetch it."""

    command_requested = pyqtSignal(str)
    photo_timer_requested = pyqtSignal(str, float)
    # The names picked out of the listing. An empty list means everything that
    # is not here yet, which is what an operator who selected nothing wants.
    fetch_requested = pyqtSignal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent, TEST_CAMERA_TEXT["card_column_title"])

        self.watching = False

        hint_label = QLabel(TEST_CAMERA_TEXT["card_column_hint"], self)
        set_role(hint_label, ROLE_HINT)
        hint_label.setWordWrap(True)

        self.start_video_button = self.build_button(
            TEST_CAMERA_TEXT["start_video_text"], START_VIDEO_ACTION
        )
        self.stop_video_button = self.build_button(
            TEST_CAMERA_TEXT["stop_video_text"], STOP_VIDEO_ACTION
        )
        set_variant(self.stop_video_button, VARIANT_CAUTION)
        self.take_photo_button = self.build_button(
            TEST_CAMERA_TEXT["take_photo_text"], TAKE_PHOTO_ACTION
        )

        self.rate_input = QDoubleSpinBox(self)
        self.rate_input.setDecimals(TEST_CAMERA_TEXT["rate_decimals"])
        self.rate_input.setRange(TEST_CAMERA_TEXT["rate_minimum"],
                                 TEST_CAMERA_TEXT["rate_maximum"])
        self.rate_input.setSingleStep(TEST_CAMERA_TEXT["rate_step"])
        self.rate_input.setValue(TEST_CAMERA_TEXT["rate_default"])
        self.rate_input.setSuffix(TEST_CAMERA_TEXT["rate_suffix"])

        rate_caption = QLabel(TEST_CAMERA_TEXT["rate_caption"], self)
        set_role(rate_caption, ROLE_READOUT_LABEL)
        rate_row = QHBoxLayout()
        flush_layout(rate_row, SPACE_SM)
        rate_row.addWidget(rate_caption)
        rate_row.addWidget(self.rate_input)

        self.start_timer_button = QPushButton(
            TEST_CAMERA_TEXT["start_timer_text"], self
        )
        self.start_timer_button.clicked.connect(self.request_photo_timer)
        self.stop_timer_button = self.build_button(
            TEST_CAMERA_TEXT["stop_timer_text"], STOP_TIMER_ACTION
        )
        set_variant(self.stop_timer_button, VARIANT_CAUTION)

        self.list_files_button = self.build_button(
            TEST_CAMERA_TEXT["list_files_text"], LIST_FILES_ACTION
        )
        set_variant(self.list_files_button, VARIANT_GHOST)

        self.fetch_button = QPushButton(TEST_CAMERA_TEXT["fetch_files_text"], self)
        self.fetch_button.clicked.connect(self.request_fetch)

        self.watch_button = QPushButton(TEST_CAMERA_TEXT["watch_on_text"], self)
        self.watch_button.clicked.connect(self.request_watch)

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)

        self.add_widget(hint_label)
        self.add_widget(self.start_video_button)
        self.add_widget(self.stop_video_button)
        self.add_widget(self.take_photo_button)
        self.add_layout(rate_row)
        self.add_widget(self.start_timer_button)
        self.add_widget(self.stop_timer_button)
        self.add_widget(self.list_files_button)
        self.add_widget(self.fetch_button)
        self.add_widget(self.watch_button)
        self.build_listing()
        self.add_widget(self.status_label)

        self.show_status("", STATE_NONE)

    def build_listing(self) -> None:
        """What the camera says is on its card, under the presses that fetch it."""
        listing_heading = QLabel(TEST_CARD_TEXT["title"], self)
        set_role(listing_heading, ROLE_SUBHEADING)

        self.count_label = QLabel(TEST_CARD_TEXT["empty_text"], self)
        set_role(self.count_label, ROLE_HINT)
        self.count_label.setWordWrap(True)

        self.file_list = QListWidget(self)
        self.file_list.setMinimumHeight(TEST_LAYOUT["monitor_minimum_height"])
        self.file_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )

        self.add_widget(listing_heading)
        self.add_widget(self.count_label)
        self.add_widget(self.file_list)

    def build_button(self, text: str, action: str) -> QPushButton:
        """A press that sends one action and nothing else with it."""
        button = QPushButton(text, self)
        button.clicked.connect(lambda: self.command_requested.emit(action))
        return button

    # The operator's side

    def request_photo_timer(self) -> None:
        self.photo_timer_requested.emit(START_TIMER_ACTION, self.rate_input.value())

    def request_fetch(self) -> None:
        chosen_names = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.file_list.selectedItems()
        ]
        self.fetch_requested.emit(chosen_names)

    def request_watch(self) -> None:
        """Ask for the opposite of what the aircraft says it is doing."""
        if self.watching:
            self.command_requested.emit(WATCH_OFF_ACTION)
            return
        self.command_requested.emit(WATCH_ON_ACTION)

    # The aircraft's side

    def show_media_list(self, media_state) -> None:
        """Redraw the listing from the last one the aircraft sent."""
        self.file_list.clear()
        for media_file in media_state.files:
            self.file_list.addItem(build_entry(media_file))

        if not media_state.has_files():
            # The camera's own words on why beat a line that guesses at it.
            self.count_label.setText(media_state.listing_reason
                                     or TEST_CARD_TEXT["empty_text"])
            return

        self.count_label.setText(
            TEST_CARD_TEXT["count_format"].format(photos=media_state.photo_count,
                                                  videos=media_state.video_count)
        )

    def show_watching(self, watching: bool) -> None:
        """Follow the aircraft's word on whether frames are still coming."""
        self.watching = watching
        if watching:
            self.watch_button.setText(TEST_CAMERA_TEXT["watch_off_text"])
            set_variant(self.watch_button, VARIANT_CAUTION)
            return
        self.watch_button.setText(TEST_CAMERA_TEXT["watch_on_text"])
        set_variant(self.watch_button, VARIANT_GHOST)

    def show_command_sent(self) -> None:
        self.show_status(TEST_CAMERA_TEXT["command_sent_text"], STATE_CAUTION)

    def show_command_accepted(self) -> None:
        self.show_status(TEST_CAMERA_TEXT["command_accepted_text"], STATE_OK)

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


def build_entry(media_file) -> QListWidgetItem:
    """One line of the listing, carrying the file name a fetch would ask for."""
    if media_file.is_photo():
        kind = TEST_CARD_TEXT["kind_photo_text"]
    else:
        kind = TEST_CARD_TEXT["kind_video_text"]

    size = TEST_CARD_TEXT["size_format"].format(megabytes=media_file.megabytes())
    if media_file.fetched:
        line = TEST_CARD_TEXT["fetched_format"]
    else:
        line = TEST_CARD_TEXT["entry_format"]

    item = QListWidgetItem(line.format(name=media_file.name, kind=kind, size=size))
    item.setData(Qt.ItemDataRole.UserRole, media_file.name)
    return item
