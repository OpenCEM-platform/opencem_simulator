import sqlite3
from clock import Clock
from typing import Optional
from interfaces import Battery, BatteryStepMode, BatteryStepInput, BatteryStepResult, PowerSource, PowerSourceStepResult, Load, LoadStepResult, Grid, GridStepInput, GridStepResult, PowerSource, PowerSourceStepResult, Inverter, InverterStepInput, InverterStepResult

class BatteryDataset(Battery):
    def __init__(self, clock: Clock, inverter_id: int, database: sqlite3.Connection):
        self.db = database
        self.clock = clock
        self.inverter_id = inverter_id
        self.nominal_voltage = 55

    def step(self, step_ticks: int, battery_input : Optional[BatteryStepInput], *args, **kwargs) -> BatteryStepResult:
        next_clock = self.clock.advance(step_ticks)
        hours_passed = Clock.difference_hours(self.clock, next_clock)
        m = interpolate_row(fetch_around_unix_ts(self.db, "analog_measurements", self.inverter_id, self.clock.to_seconds()), self.clock.to_seconds())
        discharge_energy_j = m["battvolt"] * m["battcurr"] * hours_passed * 3600
        discharge_capacity_c = discharge_energy_j / self.nominal_voltage
        self.clock = next_clock
        return BatteryStepResult(voltage_v = m["battvolt"],
                                 current_a = m["battcurr"],
                                 soc = m["battsoc"],
                                 discharge_capacity_c = discharge_capacity_c,
                                 discharge_energy_j = discharge_energy_j)

class LoadDataset(Load):
    def __init__(self, clock: Clock, inverter_id: int, database: sqlite3.Connection):
        self.db = database
        self.clock = clock
        self.inverter_id = inverter_id

    def step(self, step_ticks: int, *args, **kwargs) -> LoadStepResult:
        next_clock = self.clock.advance(step_ticks)
        m = interpolate_row(fetch_around_unix_ts(self.db, "analog_measurements", self.inverter_id, self.clock.to_seconds()), self.clock.to_seconds())
        self.clock = next_clock
        return LoadStepResult(current_a = m["outcurra"],
                              voltage_v = m["outvolta"],
                              power_apparent_va = m["outva_a"],
                              power_active_w = m["outw_a"])

class GridDataset(Grid):
    def __init__(self, clock: Clock, inverter_id: int, database: sqlite3.Connection):
        self.db = database
        self.clock = clock
        self.inverter_id = inverter_id

    def step(self, step_ticks: int, grid_input: Optional[GridStepInput], *args, **kwargs) -> GridStepResult:
        next_clock = self.clock.advance(step_ticks)
        m = interpolate_row(fetch_around_unix_ts(self.db, "analog_measurements", self.inverter_id, self.clock.to_seconds()), self.clock.to_seconds())
        self.clock = next_clock
        return GridStepResult(power_delivered_apparent_va = m["linepowerva_a"],
                              power_delivered_active_w = m["linepowerw_a"])

class PowerSourceDataset(PowerSource):
    def __init__(self, clock: Clock, inverter_id: int, database: sqlite3.Connection):
        self.db = database
        self.clock = clock
        self.inverter_id = inverter_id

    def step(self, step_ticks: int, *args, **kwargs) -> PowerSourceStepResult:
        next_clock = self.clock.advance(step_ticks)
        m = interpolate_row(fetch_around_unix_ts(self.db, "analog_measurements", self.inverter_id, self.clock.to_seconds()), self.clock.to_seconds())
        self.clock = next_clock
        return PowerSourceStepResult(voltage_v = m["pv1volt"],
                                     current_a = m["pv1curr"],
                                     power_w = m["pv1power"])

class InverterDataset(Inverter):
    def __init__(self, clock: Clock, inverter_id: int, database: sqlite3.Connection):
        self.db = database
        self.clock = clock
        self.inverter_id = inverter_id

    def step(self, step_ticks: int, inverter_input: InverterStepInput, *args, **kwargs) -> InverterStepResult:
        next_clock = self.clock.advance(step_ticks)
        m = interpolate_row(fetch_around_unix_ts(self.db, "analog_measurements", self.inverter_id, self.clock.to_seconds()), self.clock.to_seconds())
        self.clock = next_clock
        return InverterStepResult(next_battery_input = BatteryStepInput(mode = BatteryStepMode.CHARGE if m["battcurr"] < 0 else BatteryStepMode.DISCHARGE if m["battcurr"] > 0 else BatteryStepMode.IDLE,
                                                                        current_a = abs(m["battcurr"])),
                                  next_grid_input = GridStepInput(power_demand_apparent_va = m["linepowerva_a"],
                                                                  power_demand_active_w = m["linepowerw_a"]),
                                  generator_power_drawn_w = m["pv1power"])
