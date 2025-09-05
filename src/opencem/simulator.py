from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence
from interfaces import BatteryStepInput, GridStepInput, PowerSource, Battery, Load, Grid, Inverter, InverterStepInput, BatteryStepResult, GridStepResult, InverterStepResult, LoadStepResult, PowerSourceStepResult
from clock import Clock

@dataclass
class StepAggregates:
    generated_energy_wh : float
    battery_charge_energy_wh : float
    battery_discharge_energy_wh : float
    load_energy_wh : float
    generator_energy_unused_wh : float

@dataclass
class CumulativeAggregates:
    total_generated_energy_wh : float = 0
    total_battery_charge_energy_wh : float = 0
    total_battery_discharge_energy_wh : float = 0
    total_load_energy_wh : float = 0
    total_generator_energy_unused_wh : float = 0
    max_grid_power_demand_active_w : float = 0
    max_grid_power_demand_apparent_va : float = 0
    max_battery_voltage_v : float = 0
    max_battery_current_a : float = 0
    max_load_voltage_v : float = 0
    max_load_current_a : float = 0
    max_generator_voltage_v : float = 0
    max_generator_current_a : float = 0
    max_battery_soc : float = 0
    min_battery_soc : float = 0

@dataclass
class SimulatorStepResult:
    battery: BatteryStepResult
    power_source: PowerSourceStepResult
    load: LoadStepResult
    grid: GridStepResult
    inverter: InverterStepResult
    step_aggregates: StepAggregates
    cumulative_aggregates: CumulativeAggregates

class Simulator:
    def __init__(self,
                 power_source: PowerSource,
                 battery: Battery,
                 load: Load,
                 grid: Grid,
                 inverter: Inverter,
                 clock = Clock.now() ):
        self.power_source = power_source
        self.battery = battery
        self.load = load
        self.grid = grid
        self.inverter = inverter
        self.next_battery_input : Optional[BatteryStepInput] = None
        self.next_grid_input : Optional[GridStepInput] = None
        self.clock = clock
        self.last_cumulative = CumulativeAggregates()

    def step(self, step_ticks: int, *, comp_args: Mapping[str, Sequence[Any]] = {}, comp_kwargs: Mapping[str, Mapping[str, Any]] = {}):
        battery_step = self.battery.step(step_ticks, self.next_battery_input, *comp_args.get("battery", {}), **comp_kwargs.get("battery", {}))
        power_source_step = self.power_source.step(step_ticks, *comp_args.get("power_source", {}), **comp_kwargs.get("power_source", {}))
        load_step = self.load.step(step_ticks, *comp_args.get("load", {}), **comp_kwargs.get("load", {}))
        grid_step = self.grid.step(step_ticks, self.next_grid_input, *comp_args.get("grid", {}), **comp_kwargs.get("grid", {}))
        inverter_step = self.inverter.step(step_ticks, InverterStepInput(battery_step, power_source_step, load_step), *comp_args.get("inverter", {}), **comp_kwargs.get("inverter", {}))
        self.next_battery_input = inverter_step.next_battery_input
        self.next_grid_input = inverter_step.next_grid_input
        next_clock = self.clock.advance(step_ticks = step_ticks)
        hours_passed = Clock.difference_hours(self.clock, next_clock)
        step_aggregates = StepAggregates(
                generated_energy_wh = power_source_step.power_w * hours_passed,
                battery_charge_energy_wh = max(0, -battery_step.discharge_energy_j / 3600),
                battery_discharge_energy_wh = max(0, battery_step.discharge_energy_j / 3600),
                load_energy_wh = load_step.power_active_w * hours_passed,
                generator_energy_unused_wh = (power_source_step.power_w - inverter_step.generator_power_drawn_w) * hours_passed)
        cumulative_aggregates = CumulativeAggregates(
                total_generated_energy_wh = self.last_cumulative.total_generated_energy_wh + step_aggregates.generated_energy_wh,
                total_battery_charge_energy_wh = self.last_cumulative.total_battery_charge_energy_wh + step_aggregates.battery_charge_energy_wh,
                total_battery_discharge_energy_wh = self.last_cumulative.total_battery_discharge_energy_wh + step_aggregates.battery_discharge_energy_wh,
                total_load_energy_wh = self.last_cumulative.total_load_energy_wh + step_aggregates.load_energy_wh,
                total_generator_energy_unused_wh = self.last_cumulative.total_generator_energy_unused_wh + step_aggregates.generator_energy_unused_wh,
                max_grid_power_demand_active_w = max(self.last_cumulative.max_grid_power_demand_active_w, self.next_grid_input.power_demand_active_w),
                max_grid_power_demand_apparent_va = max(self.last_cumulative.max_grid_power_demand_apparent_va, self.next_grid_input.power_demand_apparent_va),
                max_battery_voltage_v = max(self.last_cumulative.max_battery_voltage_v, battery_step.voltage_v),
                max_battery_current_a = max(self.last_cumulative.max_battery_current_a, battery_step.current_a),
                max_load_voltage_v = max(self.last_cumulative.max_load_voltage_v, load_step.voltage_v),
                max_load_current_a = max(self.last_cumulative.max_load_current_a, load_step.current_a),
                max_generator_voltage_v = max(self.last_cumulative.max_generator_voltage_v, power_source_step.voltage_v),
                max_generator_current_a = max(self.last_cumulative.max_generator_current_a, power_source_step.current_a),
                max_battery_soc = max(self.last_cumulative.max_battery_soc, battery_step.soc),
                min_battery_soc = min(self.last_cumulative.min_battery_soc, battery_step.soc))
        self.last_cumulative = cumulative_aggregates
        self.clock = next_clock
        return SimulatorStepResult(battery_step, power_source_step, load_step, grid_step, inverter_step, step_aggregates, cumulative_aggregates)
