"""The mission plan the operator builds in the UPLOAD MISSION window.

A plan is an ordered list of steps. Each step knows which inputs it uses, how
it reads in the plan list and the terminal, and what it looks like on the wire —
the short ``[code, values...]`` form the drones parse. Keeping all three next to
each other means a new step type is one entry here plus one in the drones'
step table, and the window itself needs no changes at all.

Coordinates are metres in the swarm's own frame: north and east measured from
where the swarm stands when the mission starts, which is the same frame the
telemetry blocks show. A GO TO altitude is a change rather than a place — 0
keeps the height the previous step left, a negative value descends.
"""

from dataclasses import dataclass, field

from competitions.swarm_uav.config import (
    PLAN_DEFAULT_ALTITUDE_CHANGE,
    PLAN_DEFAULT_FORMATION_ANGLE,
    PLAN_DEFAULT_FORMATION_DISTANCE,
    PLAN_FORMATION_LABELS,
    PLAN_STEP_ARM,
    PLAN_STEP_DISARM,
    PLAN_STEP_FORMATION,
    PLAN_STEP_GOTO,
    PLAN_STEP_LABELS,
    PLAN_STEP_LAND,
    PLAN_STEP_TAKEOFF,
    PLAN_STEP_TEXT,
)


@dataclass(frozen=True)
class StepKind:
    """One task the operator can add, and the inputs it needs."""

    code: str
    label: str
    needs_altitude: bool = False
    needs_position: bool = False
    needs_formation: bool = False


# In the order the task picker offers them.
STEP_KINDS: list[StepKind] = [
    StepKind(PLAN_STEP_ARM, PLAN_STEP_LABELS["arm"]),
    StepKind(
        PLAN_STEP_TAKEOFF, PLAN_STEP_LABELS["takeoff"], needs_altitude=True
    ),
    StepKind(
        PLAN_STEP_GOTO, PLAN_STEP_LABELS["goto"],
        needs_altitude=True, needs_position=True,
    ),
    StepKind(
        PLAN_STEP_FORMATION, PLAN_STEP_LABELS["formation"], needs_formation=True
    ),
    StepKind(PLAN_STEP_LAND, PLAN_STEP_LABELS["land"]),
    StepKind(PLAN_STEP_DISARM, PLAN_STEP_LABELS["disarm"]),
]


@dataclass
class PlanStep:
    """One step of the plan: its kind plus the values that kind uses."""

    code: str
    altitude: float = PLAN_DEFAULT_ALTITUDE_CHANGE
    north: float = 0.0
    east: float = 0.0
    rotate_formation: bool = False
    formation_code: str = field(default_factory=lambda: next(iter(PLAN_FORMATION_LABELS)))
    formation_distance: float = PLAN_DEFAULT_FORMATION_DISTANCE
    formation_angle: float = PLAN_DEFAULT_FORMATION_ANGLE

    def description(self) -> str:
        """How the step reads in the plan list and in the terminal."""
        if self.code == PLAN_STEP_TAKEOFF:
            return PLAN_STEP_TEXT["takeoff"].format(altitude=self.altitude)
        if self.code == PLAN_STEP_GOTO:
            if self.rotate_formation:
                rotation = PLAN_STEP_TEXT["rotation_suffix"]
            else:
                rotation = ""
            return PLAN_STEP_TEXT["goto"].format(
                north=self.north,
                east=self.east,
                altitude=self.altitude,
                rotation=rotation,
            )
        if self.code == PLAN_STEP_FORMATION:
            return PLAN_STEP_TEXT["formation"].format(
                formation=PLAN_FORMATION_LABELS[self.formation_code],
                distance=self.formation_distance,
                angle=self.formation_angle,
            )
        if self.code == PLAN_STEP_ARM:
            return PLAN_STEP_TEXT["arm"]
        if self.code == PLAN_STEP_DISARM:
            return PLAN_STEP_TEXT["disarm"]
        return PLAN_STEP_TEXT["land"]

    def wire_values(self) -> list:
        """The step as the drones read it: [code, values...]."""
        if self.code == PLAN_STEP_TAKEOFF:
            return [self.code, self.altitude]
        if self.code == PLAN_STEP_GOTO:
            # The flag travels as 0/1 so the mesh line stays as short as possible.
            return [
                self.code, self.north, self.east, self.altitude,
                int(self.rotate_formation),
            ]
        if self.code == PLAN_STEP_FORMATION:
            return [
                self.code, self.formation_code,
                self.formation_distance, self.formation_angle,
            ]
        return [self.code]


def wire_steps(plan_steps: list[PlanStep]) -> list:
    """The whole plan in the form the upload message carries."""
    return [step.wire_values() for step in plan_steps]
