"""Detection approve / deny browser, loaded from designer/detection_review_panel.ui.

Detections found by the aircraft queue up here. The operator browses them, and
approves or denies the one on screen. Either verdict takes the detection out of
the queue and hands it to whoever connected the signal — that is where the
competition decides what to publish. This widget knows nothing about MQTT.
"""

import logging
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget

from config import (
    DETECTION_REVIEW_APPROVE_TEXT,
    DETECTION_REVIEW_COUNTER_FORMAT,
    DETECTION_REVIEW_IMAGE_MIN_HEIGHT,
    DETECTION_REVIEW_MAX_FRAMES,
    DETECTION_REVIEW_NO_FRAMES_TEXT,
    DETECTION_REVIEW_PENDING_FORMAT,
    DETECTION_REVIEW_REJECT_TEXT,
    DETECTION_REVIEW_TITLE,
)
from theme import flush_layout, set_state, set_surface, space_layout
from theme.tokens import AS_CARD, SPACE_SM, STATE_INFO
from widgets.detection_review.detection import Detection

logger = logging.getLogger(__name__)

FORM_PATH = Path(__file__).resolve().parents[2] / "designer" / "detection_review_panel.ui"


class DetectionReviewPanel(QWidget):
    """Queue of detections with an APPROVE / DENY verdict for each one."""

    approve_requested = pyqtSignal(object)  # the Detection the operator accepted
    reject_requested = pyqtSignal(object)
    # Fires whenever the queue length changes, so a mission bar or a counter
    # elsewhere can follow it without polling.
    queue_changed = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        uic.loadUi(FORM_PATH, self)

        self.detections: list[Detection] = []
        self.detection_index = 0
        # A competition can refuse an approval — set a callable that takes the
        # detection and returns the reason to show, or None to let it through.
        self.approve_guard = None

        self.build_appearance()

        self.set_hint("")
        self.detectionheaderlbl.setText(DETECTION_REVIEW_TITLE)
        self.approvebtn.setText(DETECTION_REVIEW_APPROVE_TEXT)
        self.rejectbtn.setText(DETECTION_REVIEW_REJECT_TEXT)
        self.detectionview.setMinimumHeight(DETECTION_REVIEW_IMAGE_MIN_HEIGHT)

        self.prevframebtn.clicked.connect(lambda: self.show_detection(self.detection_index - 1))
        self.nextframebtn.clicked.connect(lambda: self.show_detection(self.detection_index + 1))
        self.approvebtn.clicked.connect(self.request_approve)
        self.rejectbtn.clicked.connect(lambda: self.send_verdict(self.reject_requested))

        self.refresh_view()

    def build_appearance(self) -> None:
        """The panel is a card wherever it is dropped, with the shared padding."""
        set_surface(self, AS_CARD)
        space_layout(self.detectionlayout)
        flush_layout(self.detectionheaderlayout)
        flush_layout(self.framebrowselayout, SPACE_SM)
        flush_layout(self.verdictlayout)

    def add_detection(self, detection: Detection) -> None:
        """Queue an incoming detection; follow it if browsing the newest."""
        following_newest = (
            not self.detections or self.detection_index == len(self.detections) - 1
        )
        self.detections.append(detection)

        if len(self.detections) > DETECTION_REVIEW_MAX_FRAMES:
            dropped = self.detections.pop(0)
            logger.warning(
                f"Detection queue is full, oldest detection dropped unreviewed: "
                f"{dropped.detection_id()}"
            )
            if self.detection_index > 0:
                self.detection_index -= 1

        if following_newest:
            self.detection_index = len(self.detections) - 1
        self.refresh_view()

    def pending_count(self) -> int:
        return len(self.detections)

    def current_detection(self) -> Detection | None:
        if not self.detections:
            return None
        return self.detections[self.detection_index]

    def request_approve(self) -> None:
        """Approve the detection on screen, unless the competition refuses it."""
        detection = self.current_detection()
        if detection is None:
            return
        if self.approve_guard is not None:
            refusal_reason = self.approve_guard(detection)
            if refusal_reason is not None:
                self.show_notice(refusal_reason)
                logger.warning(f"Approval refused: {refusal_reason}")
                return
        self.send_verdict(self.approve_requested)

    def set_hint(self, hint: str) -> None:
        """What a verdict does here, in the competition's own words.

        Inside the card rather than above it: the consequence of APPROVE belongs
        with the buttons, not floating on the window behind them.
        """
        self.hintlbl.setText(hint)
        self.hintlbl.setVisible(bool(hint))

    def show_notice(self, notice: str) -> None:
        """An empty notice takes no room, so the buttons do not shift about."""
        self.noticelbl.setText(notice)
        self.noticelbl.setVisible(bool(notice))

    def send_verdict(self, verdict_signal) -> None:
        """Take the detection on screen out of the queue and pass it on."""
        if not self.detections:
            return
        detection = self.detections.pop(self.detection_index)
        verdict_signal.emit(detection)
        self.show_detection(self.detection_index)

    def show_detection(self, detection_index: int) -> None:
        if self.detections:
            detection_index = max(0, min(detection_index, len(self.detections) - 1))
        self.detection_index = detection_index
        self.refresh_view()

    def refresh_view(self) -> None:
        detection_count = len(self.detections)
        has_detections = detection_count > 0
        self.show_notice("")

        self.approvebtn.setEnabled(has_detections)
        self.rejectbtn.setEnabled(has_detections)
        self.prevframebtn.setEnabled(has_detections and self.detection_index > 0)
        self.nextframebtn.setEnabled(
            has_detections and self.detection_index < detection_count - 1
        )
        self.queue_changed.emit(detection_count)

        if not has_detections:
            self.detection_index = 0
            self.pendinglbl.setVisible(False)
            self.detailslbl.setText("")
            self.framecountlabel.setText(DETECTION_REVIEW_NO_FRAMES_TEXT)
            self.detectionview.show_placeholder(DETECTION_REVIEW_NO_FRAMES_TEXT)
            return

        detection = self.detections[self.detection_index]
        self.pendinglbl.setVisible(True)
        set_state(self.pendinglbl, STATE_INFO)
        self.pendinglbl.setText(DETECTION_REVIEW_PENDING_FORMAT.format(count=detection_count))
        self.detailslbl.setText(detection.details_text())
        self.framecountlabel.setText(
            DETECTION_REVIEW_COUNTER_FORMAT.format(
                index=self.detection_index + 1, count=detection_count
            )
        )
        self.detectionview.show_pixmap(detection.image)
