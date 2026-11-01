"""모든 소스를 정규화한 공통 장소 레코드."""
from dataclasses import dataclass, field

ROUTE_CLASSES = {"WalkingTrail", "RunningCourse", "BikePath"}
FACILITY_CLASSES = {"RestFacility", "ExerciseFacility", "Park", "PublicToilet"}


@dataclass
class Place:
    id: str
    source: str
    record_id: str
    cls: str
    name: str
    coords: list
    address: str = ""
    dataset: str = ""
    ref_date: str = ""
    alt_names: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)
    dist_center_km: float | None = None
    district: str | None = None

    @property
    def is_route(self):
        return self.cls in ROUTE_CLASSES
