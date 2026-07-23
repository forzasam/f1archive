from dataclasses import dataclass


@dataclass(frozen=True)
class DriverOption:
    driver_id: str
    name: str
    nationality: str = ""


@dataclass(frozen=True)
class ConstructorOption:
    constructor_id: str
    name: str
    nationality: str = ""
