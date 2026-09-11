"""The detection bench: run the detector, see what it scores, see where it puts it.

Three things down the page, and the last one is why the page exists. A delivery
lands on where the aircraft thinks the target is, so the metres between that and
where the target actually is decide whether the bottle lands on the mannequin or
in the grass beside it — and nothing else on this ground station measures that.
The controls and the list of sightings are here to make that number mean
something: which model produced it, how sure it had to be, and out of how many
frames.

Which detector actually loaded is the line to read first, and it is the one that
is easy to miss. A Hailo that will not open falls back to the CPU and keeps
detecting perfectly happily, and an afternoon spent tuning a model nobody was
running is an afternoon gone. So the fallback gets its own line, in red, with the
card behind it turning to match.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from competitions.suas.config import DETECTOR_BACKENDS, TEST_DETECTION_TEXT
from competitions.suas.widgets.command_button import command_button
from competitions.suas.widgets.test.sighting_column import SightingColumn
from competitions.suas.widgets.test.truth_point_table import TruthPointTable
from theme import flush_layout, set_role, set_state, set_variant, space_layout
from theme.tokens import (
    ROLE_READOUT_LABEL,
    SPACE_SM,
    STATE_CAUTION,
    STATE_CRITICAL,
    STATE_NONE,
    STATE_OK,
    VARIANT_CAUTION,
    VARIANT_GHOST,
    VARIANT_PRIMARY,
)
from widgets import Card

# The friendly name for each detector, kept against the spelling the aircraft
# uses so a name that arrives without a label still reads as something.
BACKEND_LABELS = {
    backend: TEST_DETECTION_TEXT["backend_labels"].get(name, backend)
    for name, backend in DETECTOR_BACKENDS.items()
}

SIGHTINGS_STRETCH = 1


class DetectionTestPanel(QWidget):
    """The detector's controls, what it saw, and how far off it put each thing."""

    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    backend_requested = pyqtSignal(str)
    confidence_requested = pyqtSignal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # What the aircraft last said the detector was doing. Unknown until it
        # says, because the button is a toggle.
        self.running = None

        self.sighting_column = SightingColumn(self)
        self.truth_table = TruthPointTable(self)

        page_layout = QVBoxLayout(self)
        space_layout(page_layout)
        page_layout.addWidget(self.build_controls())
        page_layout.addWidget(self.sighting_column, SIGHTINGS_STRETCH)
        page_layout.addWidget(self.truth_table)

        self.show_fallback(None)
        self.show_status("", STATE_NONE)

    def build_controls(self) -> Card:
        """The detector to run, the press that runs it, and the score it needs."""
        self.controls_card = Card(self, TEST_DETECTION_TEXT["title"])

        self.backend_input = QComboBox(self.controls_card)
        for backend, label in BACKEND_LABELS.items():
            self.backend_input.addItem(label, backend)
        # The chooser is left alone by anything the aircraft says: it holds what
        # was asked for, the line below holds what loaded, and the two
        # disagreeing is the answer this page is looking for.
        self.backend_input.activated.connect(self.request_backend)

        self.detect_button = command_button(
            TEST_DETECTION_TEXT["start_text"], VARIANT_PRIMARY, self.controls_card
        )
        self.detect_button.clicked.connect(self.request_detecting)

        self.confidence_input = QDoubleSpinBox(self.controls_card)
        self.confidence_input.setDecimals(TEST_DETECTION_TEXT["confidence_decimals"])
        self.confidence_input.setRange(TEST_DETECTION_TEXT["confidence_minimum"],
                                       TEST_DETECTION_TEXT["confidence_maximum"])
        self.confidence_input.setSingleStep(TEST_DETECTION_TEXT["confidence_step"])

        set_confidence_button = QPushButton(
            TEST_DETECTION_TEXT["set_confidence_text"], self.controls_card
        )
        set_variant(set_confidence_button, VARIANT_GHOST)
        set_confidence_button.clicked.connect(self.request_confidence)

        controls = QHBoxLayout()
        flush_layout(controls, SPACE_SM)
        controls.addWidget(caption(TEST_DETECTION_TEXT["backend_caption"],
                                   self.controls_card))
        controls.addWidget(self.backend_input)
        controls.addWidget(self.detect_button)
        controls.addWidget(caption(TEST_DETECTION_TEXT["confidence_caption"],
                                   self.controls_card))
        controls.addWidget(self.confidence_input)
        controls.addWidget(set_confidence_button)
        controls.addStretch()

        self.detector_label = QLabel(TEST_DETECTION_TEXT["idle_text"],
                                     self.controls_card)
        self.detector_label.setWordWrap(True)

        self.fell_back_label = QLabel(self.controls_card)
        self.fell_back_label.setWordWrap(True)
        set_state(self.fell_back_label, STATE_CRITICAL)

        self.status_label = QLabel(self.controls_card)
        self.status_label.setWordWrap(True)

        self.controls_card.add_layout(controls)
        self.controls_card.add_widget(self.detector_label)
        self.controls_card.add_widget(self.fell_back_label)
        self.controls_card.add_widget(self.status_label)
        return self.controls_card

    # The operator's side

    def request_detecting(self) -> None:
        """Ask for the opposite of what the aircraft says the detector is doing.

        The label follows the aircraft and not the click, the same way the
        record button does on the mission screen: a button that says STOP
        because somebody pressed START is a button that stops a run that never
        began. With the state unknown this asks to start, which is the harmless
        way round.
        """
        if self.running:
            self.stop_requested.emit()
            return
        self.start_requested.emit()

    def request_backend(self) -> None:
        self.backend_requested.emit(self.backend_input.currentData())

    def request_confidence(self) -> None:
        self.confidence_requested.emit(self.confidence_input.value())

    # What the aircraft says

    def show_detector(self, detector_state) -> None:
        """Follow the aircraft's word on the detector, whatever was pressed here."""
        self.running = detector_state.running

        if detector_state.running:
            self.detect_button.setText(TEST_DETECTION_TEXT["stop_text"])
            set_variant(self.detect_button, VARIANT_CAUTION)
            self.detector_label.setText(
                TEST_DETECTION_TEXT["running_format"].format(
                    backend=backend_label(detector_state.backend),
                    frames_per_second=detector_state.frames_per_second,
                    sightings=detector_state.sightings,
                )
            )
            set_state(self.detector_label, STATE_OK)
        else:
            self.detect_button.setText(TEST_DETECTION_TEXT["start_text"])
            set_variant(self.detect_button, VARIANT_PRIMARY)
            self.detector_label.setText(TEST_DETECTION_TEXT["idle_text"])
            set_state(self.detector_label, STATE_NONE)

        self.show_fallback(detector_state)
        if detector_state.reason:
            self.show_status(detector_state.reason, STATE_CAUTION)

    def show_fallback(self, detector_state) -> None:
        """Say when the detector that loaded is not the one that was asked for."""
        if detector_state is None or not detector_state.fell_back():
            self.fell_back_label.setVisible(False)
            self.controls_card.set_state(STATE_NONE)
            return

        self.fell_back_label.setText(
            TEST_DETECTION_TEXT["fell_back_format"].format(
                requested=backend_label(detector_state.requested_backend),
                backend=backend_label(detector_state.backend),
            )
        )
        self.fell_back_label.setVisible(True)
        self.controls_card.set_state(STATE_CRITICAL)

    # What the last press came to

    def show_command_sent(self) -> None:
        self.show_status(TEST_DETECTION_TEXT["command_sent_text"], STATE_CAUTION)

    def show_command_rejected(self, reason: str) -> None:
        self.show_status(
            TEST_DETECTION_TEXT["command_rejected_format"].format(reason=reason),
            STATE_CRITICAL,
        )

    def show_command_timeout(self) -> None:
        self.show_status(TEST_DETECTION_TEXT["command_timeout_text"], STATE_CRITICAL)

    def show_status(self, status: str, state: str) -> None:
        self.status_label.setText(status)
        self.status_label.setVisible(bool(status))
        set_state(self.status_label, state)


def caption(text: str, parent) -> QLabel:
    caption_label = QLabel(text, parent)
    set_role(caption_label, ROLE_READOUT_LABEL)
    return caption_label


def backend_label(backend: str) -> str:
    """The friendly name for a detector, or whatever the aircraft called it."""
    return BACKEND_LABELS.get(backend, backend)
