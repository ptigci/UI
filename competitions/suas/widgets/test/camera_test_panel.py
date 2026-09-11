"""The camera page of the TEST tab: proving the A8 mini before a flight.

Three things have to be true before the aircraft is worth launching, and each
one fails on its own. The gimbal has to move when it is told to and say where it
went. Stills have to come out of both places a still can come from. And a file
has to be able to leave the camera's own microSD card, because the Ethernet
stream the Pi reads tops out at 1080p and the card in the camera body is the
only place a 4K image ever exists.

So the page is laid out as the two places a frame is kept, either side of the
picture that is coming down now: the camera's card on the left, the RTSP stream
on the right, the gimbal along the bottom and the copy to this laptop under it.
Nothing here talks to the aircraft — every press leaves as a signal and every
number arrives through a show_ call.
"""

from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from competitions.suas.config import TEST_CAMERA_TEXT, TEST_LAYOUT
from competitions.suas.widgets.test.card_column import CardColumn
from competitions.suas.widgets.test.gimbal_bar import GimbalBar
from competitions.suas.widgets.test.stream_column import StreamColumn
from competitions.suas.widgets.test.transfer_bar import TransferBar
from theme import flush_layout, space_layout
from theme.tokens import SPACE_MD
from widgets import Card, CameraView

# The picture takes every pixel the row can spare; the two command columns are
# as wide as their buttons and no wider.
PICTURE_STRETCH = 1


class CameraTestPanel(QWidget):
    """The live picture, the presses either side of it, and the copy underneath."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Neither column is given a width. A fixed one was 260 pixels and the
        # card column's buttons need 343, so Qt squeezed the contents past the
        # size they can draw in and stacked them on top of each other. The row
        # below gives the picture the stretch and the two columns their own
        # size hint, which is the width their longest button actually is.
        self.card_column = CardColumn(self)
        self.stream_column = StreamColumn(self)

        self.camera_view = CameraView(self)
        self.camera_view.setMinimumHeight(TEST_LAYOUT["video_minimum_height"])
        self.camera_view.show_placeholder(TEST_CAMERA_TEXT["waiting_text"])

        picture_card = Card(self)
        picture_card.add_widget(self.camera_view, PICTURE_STRETCH)

        top_row = QHBoxLayout()
        flush_layout(top_row, SPACE_MD)
        top_row.addWidget(self.card_column)
        top_row.addWidget(picture_card, PICTURE_STRETCH)
        top_row.addWidget(self.stream_column)

        self.gimbal_bar = GimbalBar(self)
        self.transfer_bar = TransferBar(self)

        page_layout = QVBoxLayout(self)
        space_layout(page_layout)
        page_layout.addLayout(top_row, PICTURE_STRETCH)
        page_layout.addWidget(self.gimbal_bar)
        page_layout.addWidget(self.transfer_bar)

    def show_frame(self, frame: QPixmap) -> None:
        """Draw one preview frame."""
        self.camera_view.show_pixmap(frame)

    def show_no_picture(self, has_had_one: bool) -> None:
        """Say the feed is not live, and say which kind of not live it is.

        Never having had a picture usually means the aircraft is not powered up.
        Having lost one means the link went, and on a bench page that is the
        difference between a camera to plug in and a camera to go and look at.
        """
        if has_had_one:
            self.camera_view.show_placeholder(TEST_CAMERA_TEXT["no_signal_text"])
            return
        self.camera_view.show_placeholder(TEST_CAMERA_TEXT["waiting_text"])
