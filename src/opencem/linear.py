from dataclasses import dataclass
from opencem.clock import Clock
from typing import List, Tuple, Optional
from opencem.interfaces import Battery, BatteryStepMode, BatteryStepInput, BatteryStepResult, Grid, GridStepInput, GridStepResult, Inverter, InverterStepInput, InverterStepResult

class BatteryLinear(Battery):
    def __init__(self, clock: Clock,
                 initial_soc : float = 1.0,
                 capacity_j : float = 51.2 * 200 * 3600,
                 nominal_voltage_v : float = 51.2,
                 charge_efficiency : float = 1.0,
                 discharge_efficiency : float = 1.0):
        self.clock = clock
        self.energy_j = initial_soc * capacity_j
        self.nominal_voltage_v = nominal_voltage_v
        self.capacity_j = capacity_j
        self.charge_efficiency = charge_efficiency
        self.discharge_efficiency = discharge_efficiency

    def soc(self):
        return self.energy_j / self.capacity_j

    def step(self, step_ticks: int, battery_input : Optional[BatteryStepInput], *args, **kwargs) -> BatteryStepResult:
        next_clock = self.clock.advance(step_ticks)
        hours_passed = Clock.difference_hours(self.clock, next_clock)
        self.clock = next_clock
        if battery_input is None:
            return BatteryStepResult(voltage_v = self.nominal_voltage_v,
                                     current_a = 0,
                                     soc = self.soc(),
                                     discharge_capacity_c = 0,
                                     discharge_energy_j = 0)
        else:
            if battery_input.mode == BatteryStepMode.DISCHARGE:
                discharge_energy_j = self.nominal_voltage_v * battery_input.current_a * hours_passed * 3600 / self.discharge_efficiency
                discharge_energy_j = discharge_energy_j if discharge_energy_j <= self.energy_j else self.energy_j
            else:
                discharge_energy_j = self.nominal_voltage_v * battery_input.current_a * hours_passed * 3600 * self.charge_efficiency * -1
                discharge_energy_j = discharge_energy_j if self.energy_j - discharge_energy_j <= self.capacity_j else self.capacity_j - self.energy_j
            self.energy_j = self.energy_j - discharge_energy_j
            discharge_capacity_c = discharge_energy_j / self.nominal_voltage_v
            self.clock = next_clock
            return BatteryStepResult(voltage_v = self.nominal_voltage_v,
                                     current_a = battery_input.current_a,
                                     soc = self.soc(),
                                     discharge_capacity_c = discharge_capacity_c,
                                     discharge_energy_j = discharge_energy_j)

@dataclass
class PricedGridStepResult(GridStepResult):
    cost: float
    violation: bool

class GridPriced(Grid):
    def __init__(self, clock: Clock,
                 price_schedule : List[Tuple[float, float]] = [(0.0, 0.0)],
                 max_power_apparent_va : float = float('infinity'),
                 max_power_active_w : float = float('infinity')):
        self.clock = clock
        self.price_schedule = price_schedule # (time in  seconds since epoch, price in money unit/kWh)
        self.max_power_apparent_va = max_power_apparent_va
        self.max_power_active_w = max_power_active_w

    def step(self, step_ticks: int, grid_input: Optional[GridStepInput], *args, **kwargs) -> GridStepResult:
        next_clock = self.clock.advance(step_ticks)
        _, price = next(((i, f) for i, f in reversed(self.price_schedule) if i <= self.clock.to_seconds()), (0.,0.))
        hours = Clock.difference_hours(self.clock, next_clock)
        self.clock = next_clock
        return PricedGridStepResult(power_delivered_apparent_va = grid_input.power_demand_apparent_va if grid_input is not None else 0,
                                    power_delivered_active_w = grid_input.power_demand_active_w if grid_input is not None else 0,
                                    cost = grid_input.power_demand_active_w * hours / 1000.0 * price if grid_input is not None else 0,
                                    violation = (grid_input.power_demand_active_w > self.max_power_active_w or grid_input.power_demand_apparent_va > self.max_power_apparent_va) if grid_input is not None else False)


class InverterPVFirst(Inverter):
    def __init__(self, clock: Clock,
                 pv_to_ac_efficiency: float = 1.,
                 battery_to_ac_efficiency: float = 1.,
                 pv_to_battery_efficiency: float = 1.,
                 min_soc: float = 0.0,
                 max_soc: float = 1.0,
                 own_load_w: float = 30.0):
        self.clock = clock
        self.pv_to_ac_efficiency = pv_to_ac_efficiency
        self.battery_to_ac_efficiency = battery_to_ac_efficiency
        self.pv_to_battery_efficiency = pv_to_battery_efficiency
        self.min_soc = min_soc
        self.max_soc = max_soc
        self.own_load_w = own_load_w

    def step(self, step_ticks: int, inverter_input: InverterStepInput, *args, **kwargs) -> InverterStepResult:
        self.clock = self.clock.advance(step_ticks)
        pv_w = inverter_input.last_power_source_step.power_w
        load_w = inverter_input.last_load_step.power_active_w + self.own_load_w
        soc = inverter_input.last_battery_result.soc
        if pv_w * self.pv_to_ac_efficiency >= load_w:
            pv_remaining_w = pv_w - load_w / self.pv_to_ac_efficiency
            generator_power_drawn_w = load_w / self.pv_to_ac_efficiency
            next_grid_input = GridStepInput(power_demand_apparent_va = 0,
                                            power_demand_active_w = 0)
            if soc >= self.max_soc:
                return InverterStepResult(
                        next_battery_input = BatteryStepInput(mode = BatteryStepMode.IDLE,
                                                              current_a = 0),
                        next_grid_input = next_grid_input,
                        generator_power_drawn_w = generator_power_drawn_w)
            else:
                bat_v = inverter_input.last_battery_result.voltage_v
                battery_curr_a = pv_remaining_w * self.pv_to_battery_efficiency / bat_v
                return InverterStepResult(
                        next_battery_input = BatteryStepInput(mode = BatteryStepMode.CHARGE,
                                                              current_a = battery_curr_a),
                        next_grid_input = next_grid_input,
                        generator_power_drawn_w = pv_w)
        else:
            load_remaining_w = load_w - pv_w * self.pv_to_ac_efficiency
            if soc > self.min_soc:
                bat_v = inverter_input.last_battery_result.voltage_v
                needs_a = load_remaining_w / self.battery_to_ac_efficiency / bat_v
                return InverterStepResult(
                        next_battery_input = BatteryStepInput(mode = BatteryStepMode.DISCHARGE,
                                                              current_a = needs_a),
                        next_grid_input = GridStepInput(power_demand_apparent_va = 0,
                                                        power_demand_active_w = 0),
                        generator_power_drawn_w = pv_w)
            else:
                return InverterStepResult(
                        next_battery_input = BatteryStepInput(mode = BatteryStepMode.IDLE,
                                                              current_a = 0),
                        next_grid_input = GridStepInput(power_demand_apparent_va = load_remaining_w,
                                                        power_demand_active_w = load_remaining_w),
                        generator_power_drawn_w = pv_w)


