from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from enum import Enum
from opencem.clock import Clock

class SystemComponent(ABC):
    @abstractmethod
    def step(self, step_ticks: int, *args: Any, **kwargs: Any) -> Any:
        ...

    def context(self, *args: Any, **kwargs: Any) -> None:
        return None

    @property
    def id(self) -> str:
        ...

    @property
    def specification(self) -> Dict[str, Any]:
        ...

@dataclass
class PowerSourceStepResult:
    voltage_v: float
    current_a: float
    power_w: float

class PowerSource(SystemComponent, ABC):
    @abstractmethod
    def step(self, step_ticks: int, *args: Any, **kwargs: Any) -> PowerSourceStepResult:
        ...

class BatteryStepMode(Enum):
    CHARGE = 1
    DISCHARGE = 2
    IDLE = 3

@dataclass
class BatteryStepInput:
    mode: BatteryStepMode
    current_a: float

@dataclass
class BatteryStepResult:
    voltage_v: float
    current_a: float
    soc: float
    discharge_capacity_c: float
    discharge_energy_j: float

class Battery(SystemComponent, ABC):
    @abstractmethod
    def step(self, step_ticks: int, battery_input: Optional[BatteryStepInput], *args: Any, **kwargs: Any) -> BatteryStepResult:
        ...

@dataclass
class LoadStepResult:
    current_a: float
    voltage_v: float
    power_apparent_va: float
    power_active_w: float

class Load(SystemComponent, ABC):
    @abstractmethod
    def step(self, step_ticks: int, *args: Any, **kwargs: Any) -> LoadStepResult:
        ...

@dataclass
class GridStepInput:
    power_demand_apparent_va: float
    power_demand_active_w: float

@dataclass
class GridStepResult:
    power_delivered_apparent_va: float
    power_delivered_active_w: float

class Grid(SystemComponent, ABC):
    @abstractmethod
    def step(self, step_ticks: int, grid_input: Optional[GridStepInput], *args: Any, **kwargs: Any) -> GridStepResult: ...

@dataclass
class InverterStepInput:
    last_battery_result: BatteryStepResult
    last_power_source_step: PowerSourceStepResult
    last_load_step: LoadStepResult

@dataclass
class InverterStepResult:
    next_battery_input: BatteryStepInput
    next_grid_input: GridStepInput
    generator_power_drawn_w: float

class Inverter(SystemComponent, ABC):
    """System Component Interface for a DC->AC converter."""
    @abstractmethod
    def step(self, step_ticks: int, inverter_input: InverterStepInput, *args: Any, **kwargs: Any) -> InverterStepResult:
        ...

@dataclass
class ContextRecord:
    recorded_at: Clock
    start: Clock
    end: Clock
    source: str
    payload: Any

class Context(SystemComponent, ABC):
    @abstractmethod
    def step(self, step_ticks: int, *args: Any, **kwargs: Any) -> List[ContextRecord]:
        ...
