"""Putting one drone's link health on its connection label."""

from competitions.swarm_uav.config import LINK_HEALTH_TEXT, LINK_LOSS_WARN_PERCENT


def show_link_health(label, health) -> None:
    """Render (age_ms, rate_hz, loss_percent) on a ConnectionStatusLabel.

    None means nothing has arrived yet. The label turns red on a stale age
    the same way it always did, and now also on a loss above the configured
    share: a drone whose messages still arrive, but only half of them, is a
    link problem the age alone never showed.
    """
    if health is None:
        label.set_age(None)
        return
    age_milliseconds, rate_hz, loss_percent = health
    text = LINK_HEALTH_TEXT.format(age=age_milliseconds, rate=rate_hz, loss=loss_percent)
    label.set_link(age_milliseconds, text, loss_percent <= LINK_LOSS_WARN_PERCENT)
