"""Copying one flight day off a Pi into the folder the flight logs are kept in.

Every drone logs to its own card, and reading a flight means having all three
sets on this laptop. The copy runs here rather than on the Pi, like the push
does: this is the machine the files are coming to. The three drones land in
one folder named after the day, which is how the logs are read afterwards.
"""

from datetime import date

from competitions.swarm_uav.config import (
    DEVELOPER_LOGS,
    DEVELOPER_REPOSITORY_PATH,
    DEVELOPER_SSH_OPTIONS,
)
from competitions.swarm_uav.dev.local_process import UI_ROOT


def log_day_folder(flight_day: date) -> str:
    """What the day's folder is called, on the Pi and here alike."""
    return DEVELOPER_LOGS["day_folder"].format(
        date=flight_day.strftime(DEVELOPER_LOGS["date_format"])
    )


def log_destination(flight_day: date) -> str:
    """The day's folder under the flight logs, made when it is not there yet."""
    destination = (UI_ROOT / DEVELOPER_LOGS["destination"] / log_day_folder(flight_day)).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    return str(destination)


def fetch_arguments(host: str, flight_day: date) -> list[str]:
    """The scp that brings one day off one Pi, argument by argument.

    It gets the same ssh options as every other command here, so a Pi that is
    off says so instead of asking for a password nothing can answer.
    """
    remote_path = DEVELOPER_LOGS["remote_path"].format(
        repository=DEVELOPER_REPOSITORY_PATH, day_folder=log_day_folder(flight_day)
    )
    return [
        *DEVELOPER_LOGS["options"],
        *DEVELOPER_SSH_OPTIONS,
        f"{host}:{remote_path}",
        log_destination(flight_day),
    ]
