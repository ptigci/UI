"""Why a ping test or a link test came out the way it did, in plain words.

Reads the last ping table and the last link test and prints reasons, the one
that explains the most first: a laptop that is not on the Rocket network
explains every silent address behind it, so that is said and the rest is not.
Every sentence and threshold is in developer.toml [developer.diagnosis].
"""

from competitions.international_uav.config import (
    DEVELOPER_DIAGNOSIS,
    DEVELOPER_NETWORK,
    DEVELOPER_PASIFIK,
    KEY_RESULT_BROKER,
    KEY_RESULT_MESH_ROWS,
    KEY_RESULT_ROCKET,
    NETWORK_TEXT,
)
from competitions.international_uav.dev.network_report import NetworkReport
from competitions.international_uav.dev.vehicle_commands import Vehicle

# The mesh rows' own column names, as the probe writes them.
ROW_FROM = "from"
ROW_TO = "to"
ROW_LOSS = "loss"

LINK_LOSS = "loss"
HOST_SEPARATOR = "@"


def diagnose(report: NetworkReport | None, link_result: dict | None, agents: list[Vehicle]) -> list[str]:
    """The reasons, most explanatory first; one reassuring line when there are none."""
    if report is None:
        return [DEVELOPER_DIAGNOSIS["no_ping_test"]]
    reasons = []
    reasons.extend(rocket_path_reasons(report))
    if report.pi_reached:
        reasons.extend(pi_side_reasons(report))
    reasons.extend(link_test_reasons(link_result, agents))
    reasons.extend(agent_reasons(report, agents))
    if report.esp_port_present is False:
        reasons.append(
            DEVELOPER_DIAGNOSIS["esp_bridge_missing"].format(port=DEVELOPER_NETWORK["esp_port"])
        )
    if not reasons:
        reasons.append(DEVELOPER_DIAGNOSIS["all_clear"])
    return reasons


def rocket_path_reasons(report: NetworkReport) -> list[str]:
    """The laptop, the two Rockets and the Pi, in the order the signal travels."""
    if report.gcs_rocket_address is None:
        return [DEVELOPER_DIAGNOSIS["no_rocket_address"].format(
            addresses=NETWORK_TEXT["address_separator"].join(report.gcs_addresses),
            prefix=DEVELOPER_NETWORK["rocket_subnet_prefix"],
        )]
    if not answered(report.gcs_rocket_ground):
        return [DEVELOPER_DIAGNOSIS["ground_rocket_silent"].format(
            address=DEVELOPER_NETWORK["rocket_ground"], laptop_address=report.gcs_rocket_address
        )]
    if not answered(report.gcs_rocket_air):
        return [DEVELOPER_DIAGNOSIS["rockets_not_linked"].format(
            address=DEVELOPER_NETWORK["rocket_air"]
        )]
    if not answered(report.gcs_pasifik):
        return [DEVELOPER_DIAGNOSIS["pasifik_pi_silent"].format(
            address=DEVELOPER_NETWORK["pasifik_pi"]
        )]
    if report.pi_reached is False:
        return [DEVELOPER_DIAGNOSIS["pi_unreachable_by_ssh"].format(
            host=DEVELOPER_PASIFIK[f"{DEVELOPER_PASIFIK['ssh_connection']}_host"],
            reason=report.pi_failure,
        )]
    return []


def pi_side_reasons(report: NetworkReport) -> list[str]:
    """What the Pi could not reach: the camera, the laptop, the Rocket server."""
    reasons = []
    if report.pi_camera_address() is None:
        reasons.append(DEVELOPER_DIAGNOSIS["camera_adapter_missing"].format(
            prefix=DEVELOPER_NETWORK["camera_subnet_prefix"],
            addresses=NETWORK_TEXT["address_separator"].join(
                f"{interface} {address}" for interface, address in report.pi_addresses.items()
            ),
        ))
    elif not answered(report.pi_camera):
        reasons.append(DEVELOPER_DIAGNOSIS["camera_silent"].format(
            address=DEVELOPER_NETWORK["siyi_camera"]
        ))
    dialled_silent = not answered(report.pi_laptop_dialled)
    actual_answers = answered(report.pi_laptop_actual)
    if dialled_silent and actual_answers and report.pi_dialled_address != report.gcs_rocket_address:
        reasons.append(DEVELOPER_DIAGNOSIS["ground_address_mismatch"].format(
            dialled=report.pi_dialled_address, actual=report.gcs_rocket_address
        ))
    elif not dialled_silent and report.rocket_client_connected is False:
        reasons.append(DEVELOPER_DIAGNOSIS["pasifik_node_not_connected"].format(
            connection=report.pi_connection
        ))
    return reasons


def link_test_reasons(link_result: dict | None, agents: list[Vehicle]) -> list[str]:
    """Loss on the Rocket line, the broker and the mesh, from the last link test."""
    if link_result is None:
        return []
    reasons = []
    rocket_loss = link_loss(link_result.get(KEY_RESULT_ROCKET))
    if rocket_loss is not None and rocket_loss > DEVELOPER_DIAGNOSIS["loss_warning_percent"]:
        reasons.append(DEVELOPER_DIAGNOSIS["rocket_link_lossy"].format(loss=rocket_loss))
    broker_loss = link_loss(link_result.get(KEY_RESULT_BROKER))
    if broker_loss is not None and broker_loss > DEVELOPER_DIAGNOSIS["loss_warning_percent"]:
        reasons.append(DEVELOPER_DIAGNOSIS["broker_lossy"].format(loss=broker_loss))
    # An agent is named whichever way the bad row points: what it heard of a
    # peer, or what a peer heard of it.
    lossy_agents = {}
    for row in link_result.get(KEY_RESULT_MESH_ROWS, []):
        loss = row.get(ROW_LOSS)
        if loss is None or loss <= DEVELOPER_DIAGNOSIS["mesh_loss_warning_percent"]:
            continue
        for node_id in (row.get(ROW_FROM), row.get(ROW_TO)):
            lossy_agents[node_id] = max(loss, lossy_agents.get(node_id, 0))
    for agent in agents:

        if agent.agent_id in lossy_agents:
            reasons.append(DEVELOPER_DIAGNOSIS["agent_mesh_lossy"].format(
                agent_id=agent.agent_id, loss=lossy_agents[agent.agent_id]
            ))
    return reasons


def agent_reasons(report: NetworkReport, agents: list[Vehicle]) -> list[str]:
    reasons = []
    for agent in agents:
        result = report.gcs_agents.get(agent.agent_id)
        if result is not None and not result.answered():
            reasons.append(DEVELOPER_DIAGNOSIS["agent_unreachable"].format(
                agent_id=agent.agent_id, host=agent.host.split(HOST_SEPARATOR)[-1]
            ))
    return reasons


def answered(result) -> bool:
    return result is not None and result.answered()


def link_loss(link: dict | None) -> float | None:
    if not isinstance(link, dict):
        return None
    try:
        return float(link[LINK_LOSS])
    except (KeyError, TypeError, ValueError):
        return None
