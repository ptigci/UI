"""The LINK TEST: probes over the broker, echoed back by the aircraft.

Each probe goes out on the broker, crosses the ground services and the Rocket
line to the aircraft, and comes back the same way. What comes back says how
the whole mission path is doing: the round trip, how much it wobbles, how many
probes never returned and the longest silence. The replies arrive on the MQTT
thread and are hopped onto the Qt thread before anything is counted.
"""

import statistics
import time
from dataclasses import dataclass

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from competitions.suas.config import DEVELOPER_NETWORK, KEY_PROBE_ID

MILLISECONDS_PER_SECOND = 1000
FULL_PERCENT = 100.0
FIRST_PROBE_ID = 1


@dataclass
class ProbeResult:
    """What the probes measured. None where there was nothing to measure."""

    sent: int
    received: int
    loss_percent: float
    rtt_average_ms: float | None
    rtt_max_ms: float | None
    jitter_ms: float | None
    longest_gap_ms: float | None


@dataclass
class LinkTestResult:
    """The probes, and how every other link looked when they finished."""

    probes: ProbeResult
    telemetry_age_s: float | None
    safety_heartbeat_age_s: float | None
    broker_connected: bool
    video_frame_age_s: float | None
    mission_link_up: bool
    safety_link_up: bool


class LinkProbe(QObject):
    """One run of probes: sends them, collects the echoes, sums them up."""

    finished = pyqtSignal(object)
    # The echo lands on the MQTT thread; this carries it across.
    reply_received = pyqtSignal(object)

    def __init__(self, controller, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.next_probe_id = FIRST_PROBE_ID
        # Probe id -> when it left; probe id -> its round trip once it is back.
        self.sent_monotonic: dict[int, float] = {}
        self.round_trips_ms: dict[int, float] = {}
        self.reply_monotonic: list[float] = []

        self.send_timer = QTimer(self)
        self.send_timer.setInterval(DEVELOPER_NETWORK["probe_interval_ms"])
        self.send_timer.timeout.connect(self.send_probe)
        self.finish_timer = QTimer(self)
        self.finish_timer.setSingleShot(True)
        self.finish_timer.setInterval(DEVELOPER_NETWORK["probe_timeout_ms"])
        self.finish_timer.timeout.connect(self.finish)
        self.reply_received.connect(self.take_reply)

    def start(self) -> None:
        self.controller.on_link_probe_reply = self.reply_received.emit
        self.send_probe()
        self.send_timer.start()

    def stop(self) -> None:
        self.send_timer.stop()
        self.finish_timer.stop()
        self.controller.on_link_probe_reply = None

    def send_probe(self) -> None:
        probe_id = self.next_probe_id
        self.next_probe_id += 1
        self.sent_monotonic[probe_id] = time.monotonic()
        self.controller.send_link_probe(probe_id, time.time())
        if len(self.sent_monotonic) >= DEVELOPER_NETWORK["probe_count"]:
            # The last one is out; the stragglers get their timeout to come back.
            self.send_timer.stop()
            self.finish_timer.start()

    def take_reply(self, payload: dict) -> None:
        try:
            probe_id = int(payload.get(KEY_PROBE_ID))
        except (TypeError, ValueError):
            return
        if probe_id not in self.sent_monotonic or probe_id in self.round_trips_ms:
            return
        now = time.monotonic()
        self.round_trips_ms[probe_id] = (now - self.sent_monotonic[probe_id]) * MILLISECONDS_PER_SECOND
        self.reply_monotonic.append(now)

    def finish(self) -> None:
        self.controller.on_link_probe_reply = None
        self.finished.emit(self.result())

    def result(self) -> ProbeResult:
        sent = len(self.sent_monotonic)
        received = len(self.round_trips_ms)
        loss_percent = FULL_PERCENT
        if sent:
            loss_percent = (sent - received) / sent * FULL_PERCENT
        # In the order the probes went out, so the jitter is between neighbours.
        round_trips = [self.round_trips_ms[probe_id] for probe_id in sorted(self.round_trips_ms)]
        return ProbeResult(
            sent, received, loss_percent,
            average_or_none(round_trips), max_or_none(round_trips),
            average_or_none(differences(round_trips)),
            max_or_none(differences(self.reply_monotonic, MILLISECONDS_PER_SECOND)),
        )


def differences(values: list[float], scale: float = 1.0) -> list[float]:
    """The step between each value and the one before it."""
    return [abs(later - earlier) * scale for earlier, later in zip(values, values[1:])]


def average_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return statistics.fmean(values)


def max_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return max(values)
