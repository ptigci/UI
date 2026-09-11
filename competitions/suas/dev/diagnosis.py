"""Why a ping test or a link test came out the way it did, in plain words.

Reads the last ping table and the last link test and prints reasons, the one
that explains the most first: a laptop that is not on the Rocket network
explains every silent address behind it, so that is said and the rest is not.
Every sentence and threshold is in developer.toml [developer.diagnosis].
"""

from competitions.suas.config import DEVELOPER_DIAGNOSIS, DEVELOPER_NETWORK, NETWORK_TEXT
from competitions.suas.dev.link_probe import LinkTestResult
from competitions.suas.dev.network_report import NetworkReport
from competitions.suas.dev.vtol_commands import vtol_address, vtol_host

NO_REPLIES = 0


def diagnose(report: NetworkReport | None, link_result: LinkTestResult | None) -> list[str]:
    """The reasons, most explanatory first; one reassuring line when there are none."""
    if report is None:
        return [DEVELOPER_DIAGNOSIS["no_ping_test"]]
    reasons = rocket_path_reasons(report)
    if report.pi_reached:
        reasons.extend(pi_side_reasons(report))
    reasons.extend(link_test_reasons(link_result))
    if not reasons:
        reasons.append(DEVELOPER_DIAGNOSIS["all_clear"])
    return reasons


def rocket_path_reasons(report: NetworkReport) -> list[str]:
    """The laptop, the two Rockets and the Pi, in the order the signal travels."""
    laptop_address = report.gcs_rocket_address()
    if laptop_address is None:
        return [DEVELOPER_DIAGNOSIS["no_rocket_address"].format(
            addresses=NETWORK_TEXT["address_separator"].join(report.gcs_addresses),
            prefix=DEVELOPER_NETWORK["gcs_rocket_subnet"],
        )]
    if not answered(report.gcs_ping, DEVELOPER_NETWORK["rocket_ground"]):
        return [DEVELOPER_DIAGNOSIS["ground_rocket_silent"].format(
            address=DEVELOPER_NETWORK["rocket_ground"], laptop_address=laptop_address
        )]
    if not answered(report.gcs_ping, DEVELOPER_NETWORK["rocket_air"]):
        return [DEVELOPER_DIAGNOSIS["rockets_not_linked"].format(
            address=DEVELOPER_NETWORK["rocket_air"]
        )]
    if not answered(report.gcs_ping, vtol_address()):
        return [DEVELOPER_DIAGNOSIS["pi_silent"].format(address=vtol_address())]
    if report.pi_reached is False:
        return [DEVELOPER_DIAGNOSIS["pi_unreachable_by_ssh"].format(
            host=vtol_host(), reason=report.pi_failure
        )]
    return []


def pi_side_reasons(report: NetworkReport) -> list[str]:
    """What the Pi could not reach: the camera, the laptop, the Rocket server."""
    reasons = []
    if report.pi_siyi_address() is None:
        reasons.append(DEVELOPER_DIAGNOSIS["camera_adapter_missing"].format(
            prefix=DEVELOPER_NETWORK["siyi_subnet"],
            addresses=NETWORK_TEXT["address_separator"].join(
                NETWORK_TEXT["interface_format"].format(interface=interface, address=address)
                for interface, address in report.pi_addresses.items()
            ),
        ))
    elif not answered(report.pi_ping, DEVELOPER_NETWORK["siyi"]):
        reasons.append(DEVELOPER_DIAGNOSIS["camera_silent"].format(
            address=DEVELOPER_NETWORK["siyi"]
        ))
    dialled = DEVELOPER_NETWORK["link_ground_host"]
    actual = report.gcs_rocket_address()
    dialled_answers = answered(report.pi_ping, dialled)
    actual_answers = answered(report.pi_ping, actual)
    if not dialled_answers and actual_answers and dialled != actual:
        reasons.append(DEVELOPER_DIAGNOSIS["ground_address_mismatch"].format(
            dialled=dialled, actual=actual
        ))
    elif dialled_answers and report.rocket_client_seen is False:
        reasons.append(DEVELOPER_DIAGNOSIS["vtol_node_not_connected"])
    return reasons


def link_test_reasons(link_result: LinkTestResult | None) -> list[str]:
    """Loss on the probes, and the links the interface watches on its own."""
    if link_result is None:
        return []
    reasons = []
    probes = link_result.probes
    if not link_result.broker_connected:
        reasons.append(DEVELOPER_DIAGNOSIS["broker_disconnected"])
    elif probes.received == NO_REPLIES:
        reasons.append(DEVELOPER_DIAGNOSIS["probes_unanswered"])
    elif probes.loss_percent > DEVELOPER_NETWORK["loss_warning_percent"]:
        reasons.append(DEVELOPER_DIAGNOSIS["rocket_link_lossy"].format(loss=probes.loss_percent))
    if not link_result.mission_link_up:
        reasons.append(DEVELOPER_DIAGNOSIS["mission_link_down"])
    if not link_result.safety_link_up:
        reasons.append(DEVELOPER_DIAGNOSIS["safety_link_down"])
    return reasons


def answered(pings: dict[str, float | None], host: str | None) -> bool:
    if host is None:
        return False
    return pings.get(host) is not None
