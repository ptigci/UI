"""One ssh process, and its output line by line.

Both kinds of remote work look the same to Qt: a process that prints and exits
(start, stop, git pull) or one that prints until it is stopped (the live
journal). QProcess runs them without blocking the interface, so a Pi that is
off simply reports a failure a few seconds later instead of freezing the
window.
"""

import logging

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

from competitions.swarm_uav.config import (
    DEVELOPER_SSH_OPTIONS,
    DEVELOPER_SSH_PROGRAM,
    DEVELOPER_STOP_WAIT_MS,
)

logger = logging.getLogger(__name__)

LINE_SEPARATOR = "\n"
# An ssh that never started has no exit code of its own, so the session invents
# one: any non-zero code reads as a failure to whoever is watching.
START_FAILURE_EXIT_CODE = -1


class SshSession(QObject):
    """A command running on one Pi. Every line it prints arrives as a signal."""

    line_received = pyqtSignal(str)
    finished = pyqtSignal(int)

    def __init__(self, host: str, remote_command: str, parent=None) -> None:
        super().__init__(parent)
        self.host = host
        self.remote_command = remote_command
        # ssh writes its own errors to stderr, and those are exactly what the
        # operator needs to see, so both channels go to the same terminal.
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.partial_line = ""

        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.report_finished)
        self.process.errorOccurred.connect(self.report_error)

    def start(self) -> None:
        arguments = [*DEVELOPER_SSH_OPTIONS, self.host, self.remote_command]
        logger.info(f"Running on {self.host}: {self.remote_command}")
        self.process.start(DEVELOPER_SSH_PROGRAM, arguments)

    def stop(self) -> None:
        """Ask the process to go, then insist.

        Windows has no way to ask a console process to close, so terminate()
        never reaches ssh there and the kill is what actually ends it.
        """
        if self.process.state() == QProcess.ProcessState.NotRunning:
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
        logger.error(f"Could not start '{DEVELOPER_SSH_PROGRAM}' for {self.host}.")
        self.line_received.emit(self.process.errorString())
        self.finished.emit(START_FAILURE_EXIT_CODE)
