"""One log file per test, so a failed camera run is one file and not a haystack.

A bench day presses a lot of buttons. When one of them does not do what it
should, the question is always the same — what went out, what came back, and
what the aircraft was reporting in between — and answering it from the
application's own log means reading past four other tests to find the one that
matters.

So each page of the TEST tab writes its own file. It is opened when the page is
first shown, named with the time it started, and it carries two things: every
press the tab makes on that page with the answer the aircraft gave it, and
whatever the modules behind that page log while it is open. The application's
log keeps everything as it always did; these are copies of one page's share.

The files are never the record of a scored mission. That is the flight log the
aircraft writes, and nothing here replaces it.
"""

import logging
import time
from pathlib import Path

from competitions.suas.config import TEST_LOGGING, competition_path

logger = logging.getLogger(__name__)

# The logger a page's own lines are written through: "the TEST tab, this page".
PAGE_LOGGER_FORMAT = "competitions.suas.test.{page}"


class TestPageLog:
    """The log file of one page of the TEST tab."""

    def __init__(self, page_key: str) -> None:
        """Open the file and start collecting into it.

        Parameters:
            page_key (str): Which page, as ``config/test.toml`` names it.

        A file that cannot be opened costs the log and nothing else: the test
        itself still runs, and a bench that stopped because a folder was
        read-only would be a worse tool than one with no log at all.
        """
        self.page_key = page_key
        self.page_logger = logging.getLogger(PAGE_LOGGER_FORMAT.format(page=page_key))
        self.handler = None
        self.attached_loggers = []
        self.path = None

        folder = competition_path(TEST_LOGGING["folder"])
        try:
            folder.mkdir(parents=True, exist_ok=True)
            self.path = folder / TEST_LOGGING["name_format"].format(
                page=page_key,
                stamp=time.strftime(TEST_LOGGING["stamp_format"]),
            )
            self.handler = logging.FileHandler(self.path, encoding="utf-8")
        except OSError as error:
            logger.warning(f"No log file for the {page_key} test: {error}")
            return

        self.handler.setFormatter(logging.Formatter(
            TEST_LOGGING["line_format"], TEST_LOGGING["time_format"]
        ))
        # The page's own lines go in whatever the application's level is set
        # to: the presses are most of what makes the file worth reading, and a
        # file with only the failures in it does not say what led to them.
        self.page_logger.setLevel(TEST_LOGGING["level"])
        self.attach()
        remove_old_files(folder, page_key)

    def attach(self) -> None:
        """Collect this page's own lines and its modules' logging into the file."""
        for name in [self.page_logger.name] + TEST_LOGGING["loggers"][self.page_key]:
            collected = logging.getLogger(name)
            collected.addHandler(self.handler)
            self.attached_loggers.append(collected)

    def note(self, text: str) -> None:
        """Write one line about what the page just did."""
        self.page_logger.info(text)

    def note_problem(self, text: str) -> None:
        """Write one line about something the page could not do.

        A refusal from the aircraft is the most useful line in the file and the
        one somebody scrolls back to find, so it is not written at the same
        level as everything else.
        """
        self.page_logger.warning(text)

    def close(self) -> None:
        """Stop collecting and let go of the file."""
        if self.handler is None:
            return
        for collected in self.attached_loggers:
            collected.removeHandler(self.handler)
        self.attached_loggers = []
        self.handler.close()
        self.handler = None


def remove_old_files(folder: Path, page_key: str) -> None:
    """Keep the newest few of this page's files and delete the rest.

    A bench day opens a page a dozen times and every one writes a file. Without
    this the folder is unreadable by the afternoon, which defeats the point of
    splitting them up in the first place.
    """
    pattern = TEST_LOGGING["name_format"].format(page=page_key, stamp="*")
    files = sorted(folder.glob(pattern))
    for old_file in files[:-TEST_LOGGING["keep_files"]]:
        try:
            old_file.unlink()
        except OSError as error:
            logger.warning(f"Could not remove the old log {old_file}: {error}")
