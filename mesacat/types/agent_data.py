from dataclasses import dataclass
from shapely import Point


@dataclass
class AgentData:
    agent_type: int
    walking_speed: float
    home_osmid: int
    work_osmid: int
    school_osmid: int
    geometry: Point
