"""A program running on this laptop, started and stopped from the tab.

The ground station runs here, and so do the agents and the Pasifik in
simulation: SITL and the UDP mesh live on this machine, so there is no ssh in
the way. The push to a Pi runs here as well, because it is this laptop's
checkout that sends it. Each is a QProcess with the same line signals as an
ssh session, so the tab shows its output the same way.
"""

import logging
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal

from competitions.international_uav.config import DEVELOPER_LOCAL, DEVELOPER_STOP_WAIT_MS

logger = logging.getLogger(__name__)

LINE_SEPARATOR = "\n"
START_FAILURE_EXIT_CODE = -1
# competitions/international_uav/dev/local_process.py -> the UI root.
UI_ROOT = Path(__file__).resolve().parents[3]


def local_python(app: dict) -> str:
    """The app's venv interpreter when it is there, the fallback when it is not."""
    venv_python = UI_ROOT / app["python"]
    if venv_python.exists():
        return str(venv_python)
    logger.warning(f"No interpreter at {venv_python}; using '{DEVELOPER_LOCAL['fallback_python']}'.")
    return DEVELOPER_LOCAL["fallback_python"]


class LocalProcess(QObject):
    """One program running here. Every line it prints arrives as a signal."""

    line_received = pyqtSignal(str)
    finished = pyqtSignal(int)

    def __init__(
        self, program: str, arguments: list[str], directory: str, environment: dict, parent=None
    ) -> None:
        """directory is relative to the UI root; environment is added to this one's."""
        super().__init__(parent)
        self.program = program
        self.arguments = arguments
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.setWorkingDirectory(str(UI_ROOT / directory))
        process_environment = QProcessEnvironment.systemEnvironment()
        for name, value in environment.items():
            process_environment.insert(name, value)
        self.process.setProcessEnvironment(process_environment)
        self.partial_line = ""
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.report_finished)
        self.process.errorOccurred.connect(self.report_error)

    def is_running(self) -> bool:
        return self.process.state() != QProcess.ProcessState.NotRunning

    def start(self) -> None:
        command_text = " ".join([self.program, *self.arguments])
        logger.info(f"Starting {command_text} in {self.process.workingDirectory()}.")
        self.process.start(self.program, self.arguments)

    def stop(self) -> None:
        """Kill it. Windows cannot ask a console process to close, so the
        node does not get the clean shutdown Ctrl+C would give it."""
        if not self.is_running():
            return
        self.process.terminate()
        if not self.process.waitForFinished(DEVELOPER_STOP_WAIT_MS):
            self.process.kill()

    def read_output(self) -> None:
        """Emit whole lines only; a read can end in the middle of one."""
        output = bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        *complete_lines, self.partial_line = (self.partial_line + output).split(LINE_SEPARATOR)
        for line in complete_lines:
            self.line_received.emit(line.rstrip())

    def report_finished(self, exit_code: int) -> None:
        if self.partial_line:
            self.line_received.emit(self.partial_line)
            self.partial_line = ""
        self.finished.emit(exit_code)

    def report_error(self, error) -> None:
        """A process that never started emits no finished signal of its own."""
        if error != QProcess.ProcessError.FailedToStart:
            return
        logger.error(f"Could not start '{self.process.program()}' in {self.process.workingDirectory()}.")
        self.line_received.emit(self.process.errorString())
        self.finished.emit(START_FAILURE_EXIT_CODE)


def local_app(app: dict, arguments: list[str], parent=None) -> LocalProcess:
    """One of the apps under [developer.local]: its own python and its main.py."""
    return LocalProcess(
        local_python(app),
        [DEVELOPER_LOCAL["script"], *arguments],
        app["directory"],
        DEVELOPER_LOCAL["environment"],
        parent,
    )
