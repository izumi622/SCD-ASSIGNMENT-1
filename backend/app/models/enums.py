from enum import Enum
from typing import Dict, Set


class Category(str, Enum):
    water = "water"
    electricity = "electricity"
    sanitation = "sanitation"
    roads = "roads"
    streetlights = "streetlights"
    other = "other"


class Priority(str, Enum):
    high = "high"
    normal = "normal"
    low = "low"


class Status(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    rejected = "rejected"


# Explicit state transition table as mandated by §2.2
# open -> in_progress -> resolved
# open -> rejected
# in_progress -> rejected
# resolved and rejected are terminal
VALID_TRANSITIONS: Dict[Status, Set[Status]] = {
    Status.open: {Status.in_progress, Status.rejected},
    Status.in_progress: {Status.resolved, Status.rejected},
    Status.resolved: set(),
    Status.rejected: set(),
}


def is_valid_transition(current: Status, target: Status) -> bool:
    """Checks whether transitioning from current to target status is valid."""
    return target in VALID_TRANSITIONS.get(current, set())
