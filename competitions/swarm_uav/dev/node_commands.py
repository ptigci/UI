"""The commands the DEV tab runs, filled in for one drone.

Every template comes from config/developer.toml, so a moved repository or a
renamed unit is one edit there and nothing here changes. Most are shell lines
for a Pi; the push is an argument list, because that one runs as a git here.
"""

from competitions.swarm_uav.config import (
    DEVELOPER_COMMAND_CHECKOUT,
    DEVELOPER_COMMAND_REBOOT,
    DEVELOPER_COMMAND_RESTORE,
    DEVELOPER_COMMAND_MONITOR,
    DEVELOPER_COMMAND_PPS_CHECK,
    DEVELOPER_COMMAND_PULL,
    DEVELOPER_COMMAND_START,
    DEVELOPER_COMMAND_STOP,
    DEVELOPER_HOST_PATTERN,
    DEVELOPER_PUSH,
    DEVELOPER_REPOSITORY_PATH,
    DEVELOPER_SSH_OPTIONS,
    DEVELOPER_SSH_PROGRAM,
    DEVELOPER_SUDO_PASSWORD,
    DEVELOPER_SUDO_PREFIX,
    DEVELOPER_SUDO_PREFIX_WITH_PASSWORD,
    DEVELOPER_UNIT_NAME,
)


def host_for(drone_id: int) -> str:
    return DEVELOPER_HOST_PATTERN.format(drone_id=drone_id)


def start_command(drone_id: int) -> str:
    return DEVELOPER_COMMAND_START.format(
        unit=DEVELOPER_UNIT_NAME, repository=DEVELOPER_REPOSITORY_PATH, drone_id=drone_id
    )


def stop_command() -> str:
    return DEVELOPER_COMMAND_STOP.format(unit=DEVELOPER_UNIT_NAME)


def monitor_command() -> str:
    return DEVELOPER_COMMAND_MONITOR.format(unit=DEVELOPER_UNIT_NAME)


def pull_command() -> str:
    return DEVELOPER_COMMAND_PULL.format(repository=DEVELOPER_REPOSITORY_PATH)


def push_arguments(drone_id: int) -> list[str]:
    """The git push that sends this laptop's branch to one Pi, argument by argument."""
    return [
        argument.format(host=host_for(drone_id), repository=DEVELOPER_REPOSITORY_PATH)
        for argument in DEVELOPER_PUSH["arguments"]
    ]


def push_environment() -> dict:
    """git starts its own ssh, so it gets the one the other commands run with."""
    ssh_command = " ".join([DEVELOPER_SSH_PROGRAM, *DEVELOPER_SSH_OPTIONS])
    return {DEVELOPER_PUSH["ssh_variable"]: ssh_command}


def restore_command() -> str:
    return DEVELOPER_COMMAND_RESTORE.format(repository=DEVELOPER_REPOSITORY_PATH)


def pps_check_command() -> str:
    return DEVELOPER_COMMAND_PPS_CHECK.format(repository=DEVELOPER_REPOSITORY_PATH)


def reboot_command() -> str:
    """The reboot, run under sudo the way the Pis are set up to accept it."""
    if DEVELOPER_SUDO_PASSWORD:
        sudo_prefix = DEVELOPER_SUDO_PREFIX_WITH_PASSWORD.format(
            password=DEVELOPER_SUDO_PASSWORD
        )
    else:
        sudo_prefix = DEVELOPER_SUDO_PREFIX
    return DEVELOPER_COMMAND_REBOOT.format(sudo=sudo_prefix)


def checkout_command(branch: str) -> str:
    return DEVELOPER_COMMAND_CHECKOUT.format(
        repository=DEVELOPER_REPOSITORY_PATH, branch=branch
    )
