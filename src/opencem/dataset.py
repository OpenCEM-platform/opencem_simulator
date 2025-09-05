import sqlite3
from opencem.clock import Clock
import numpy as np
from typing import Optional, List
from opencem.interfaces import Battery, BatteryStepMode, BatteryStepInput, BatteryStepResult, PowerSource, PowerSourceStepResult, Load, LoadStepResult, Grid, GridStepInput, GridStepResult, PowerSource, PowerSourceStepResult, Inverter, InverterStepInput, InverterStepResult, Context, ContextRecord

def load_context(con: sqlite3.Connection, now : Clock, location : str) -> List[ContextRecord]:
    cur = con.cursor()
    query = f"""
        SELECT recorded, start, end, source, value 
        FROM textual
        WHERE end >= {now.to_seconds()} AND location LIKE '%{location}%'
    """
    cur.execute(query)
    rows = cur.fetchall()
    return [ContextRecord(Clock.from_seconds(r[0]), Clock.from_seconds(r[1]), Clock.from_seconds(r[2]), r[3], r[4]) for r in rows]

def load_inverter_array(con: sqlite3.Connection, col : str, inv : int, ts : float):
    cur = con.cursor()
    query = f"""
        SELECT read_ts, {col}
        FROM analog_measurements
        WHERE inverter = :inv
          AND {col} IS NOT NULL
          AND read_ts >= (
              SELECT read_ts
              FROM analog_measurements
              WHERE inverter = :inv
                AND {col} IS NOT NULL
                AND read_ts <= :ts
              ORDER BY read_ts DESC
              LIMIT 1
          )
        ORDER BY read_ts
    """
    cur.execute(query, {"inv": inv, "ts": ts})
    rows = cur.fetchall()
    return np.array(rows, dtype=float)

def interpolate_value(arr, ts : float) -> float:
    """
    Linearly interpolate the value at a given timestamp.
    
    arr: numpy array of shape (n,2), with [read_ts, value]
    ts:  float (epoch seconds)
    """
    times = arr[:,0]
    values = arr[:,1]

    if ts > times[-1]:
        raise ValueError(f"Timestamp {ts} is beyond last row {times[-1]}")

    idx = np.searchsorted(times, ts)
    if times[idx-1] == ts:
        return values[idx-1]

    t0, t1 = times[idx-1], times[idx]
    v0, v1 = values[idx-1], values[idx]
    frac = (ts - t0) / (t1 - t0)
    return v0 + frac * (v1 - v0)


class BatteryDataset(Battery):
    def __init__(self, clock: Clock, inverter_id: int, database: sqlite3.Connection):
        self.clock = clock
        self.battvolt = load_inverter_array(con = database, col = "battvolt", inv = inverter_id, ts = clock.to_seconds())
        self.battcurr = load_inverter_array(con = database, col = "battcurr", inv = inverter_id, ts = clock.to_seconds())
        self.battsoc  = load_inverter_array(con = database, col = "battsoc", inv = inverter_id, ts = clock.to_seconds())
        self.nominal_voltage = 55

    def step(self, step_ticks: int, battery_input : Optional[BatteryStepInput], *args, **kwargs) -> BatteryStepResult:
        next_clock = self.clock.advance(step_ticks)
        hours_passed = Clock.difference_hours(self.clock, next_clock)
        battvolt = interpolate_value(arr = self.battvolt, ts = self.clock.to_seconds())
        battcurr = interpolate_value(arr = self.battcurr, ts = self.clock.to_seconds())
        battsoc = interpolate_value(arr = self.battsoc, ts = self.clock.to_seconds())
        discharge_energy_j = battvolt * battcurr * hours_passed * 3600
        discharge_capacity_c = discharge_energy_j / self.nominal_voltage
        self.clock = next_clock
        return BatteryStepResult(voltage_v = battvolt or self.nominal_voltage,
                                 current_a = battcurr or 0,
                                 soc = battsoc / 100 or 0,
                                 discharge_capacity_c = discharge_capacity_c or 0,
                                 discharge_energy_j = discharge_energy_j or 0)

class LoadDataset(Load):
    def __init__(self, clock: Clock, inverter_id: int, database: sqlite3.Connection):
        self.clock = clock
        self.outcurra = load_inverter_array(con = database, col = "outcurra", inv = inverter_id, ts = clock.to_seconds())
        self.outvolta = load_inverter_array(con = database, col = "outvolta", inv = inverter_id, ts = clock.to_seconds())
        self.outva_a  = load_inverter_array(con = database, col = "outva_a", inv = inverter_id, ts = clock.to_seconds())
        self.outw_a   = load_inverter_array(con = database, col = "outw_a", inv = inverter_id, ts = clock.to_seconds())

    def step(self, step_ticks: int, *args, **kwargs) -> LoadStepResult:
        next_clock = self.clock.advance(step_ticks)
        outcurra = interpolate_value(arr = self.outcurra, ts = self.clock.to_seconds())
        outvolta = interpolate_value(arr = self.outvolta, ts = self.clock.to_seconds())
        outva_a = interpolate_value(arr = self.outva_a, ts = self.clock.to_seconds())
        outw_a = interpolate_value(arr = self.outw_a, ts = self.clock.to_seconds())
        self.clock = next_clock
        return LoadStepResult(current_a = outcurra,
                              voltage_v = outvolta,
                              power_apparent_va = outva_a,
                              power_active_w = outw_a)

class GridDataset(Grid):
    def __init__(self, clock: Clock, inverter_id: int, database: sqlite3.Connection):
        self.clock = clock
        self.linepowerva_a = load_inverter_array(con = database, col = "linepowerva_a", inv = inverter_id, ts = clock.to_seconds())
        self.linepowerw_a = load_inverter_array(con = database, col = "linepowerw_a", inv = inverter_id, ts = clock.to_seconds())

    def step(self, step_ticks: int, grid_input: Optional[GridStepInput], *args, **kwargs) -> GridStepResult:
        next_clock = self.clock.advance(step_ticks)
        linepowerva_a = interpolate_value(arr = self.linepowerva_a, ts = self.clock.to_seconds())
        linepowerw_a = interpolate_value(arr = self.linepowerw_a, ts = self.clock.to_seconds())
        self.clock = next_clock
        return GridStepResult(power_delivered_apparent_va = linepowerva_a,
                              power_delivered_active_w = linepowerw_a)

class PowerSourceDataset(PowerSource):
    def __init__(self, clock: Clock, inverter_id: int, database: sqlite3.Connection):
        self.pv1volt = load_inverter_array(con = database, col = "pv1volt", inv = inverter_id, ts = clock.to_seconds())
        self.pv1curr = load_inverter_array(con = database, col = "pv1curr", inv = inverter_id, ts = clock.to_seconds())
        self.pv1power = load_inverter_array(con = database, col = "pv1power", inv = inverter_id, ts = clock.to_seconds())
        self.clock = clock

    def step(self, step_ticks: int, *args, **kwargs) -> PowerSourceStepResult:
        next_clock = self.clock.advance(step_ticks)
        pv1volt = interpolate_value(arr = self.pv1volt, ts = self.clock.to_seconds())
        pv1curr = interpolate_value(arr = self.pv1curr, ts = self.clock.to_seconds())
        pv1power = interpolate_value(arr = self.pv1power, ts = self.clock.to_seconds())
        self.clock = next_clock
        return PowerSourceStepResult(voltage_v = pv1volt,
                                     current_a = pv1curr,
                                     power_w = pv1power)

class InverterDataset(Inverter):
    def __init__(self, clock: Clock, inverter_id: int, database: sqlite3.Connection):
        self.clock = clock
        self.battcurr = load_inverter_array(con = database, col = "battcurr", inv = inverter_id, ts = clock.to_seconds())
        self.linepowerw_a = load_inverter_array(con = database, col = "linepowerw_a", inv = inverter_id, ts = clock.to_seconds())
        self.linepowerva_a = load_inverter_array(con = database, col = "linepowerva_a", inv = inverter_id, ts = clock.to_seconds())
        self.pv1power = load_inverter_array(con = database, col = "pv1power", inv = inverter_id, ts = clock.to_seconds())

    def step(self, step_ticks: int, inverter_input: InverterStepInput, *args, **kwargs) -> InverterStepResult:
        next_clock = self.clock.advance(step_ticks)
        battcurr = interpolate_value(arr = self.battcurr, ts = self.clock.to_seconds())
        pv1power = interpolate_value(arr = self.pv1power, ts = self.clock.to_seconds())
        linepowerva_a = interpolate_value(arr = self.linepowerva_a, ts = self.clock.to_seconds())
        linepowerw_a = interpolate_value(arr = self.linepowerw_a, ts = self.clock.to_seconds())
        self.clock = next_clock
        return InverterStepResult(next_battery_input = BatteryStepInput(mode = BatteryStepMode.CHARGE if battcurr < 0 else BatteryStepMode.DISCHARGE if battcurr > 0 else BatteryStepMode.IDLE,
                                                                        current_a = abs(battcurr)),
                                  next_grid_input = GridStepInput(power_demand_apparent_va = linepowerva_a,
                                                                  power_demand_active_w = linepowerw_a),
                                  generator_power_drawn_w = pv1power)

class ContextDataset(Context):
    def __init__(self, clock: Clock, location: str, horizon_ticks: int, database: sqlite3.Connection):
        self.clock = clock
        self.all_context = load_context(database, clock, location)
        self.horizon = horizon_ticks

    def step(self, step_ticks: int) -> List[ContextRecord]:
        now = self.clock
        self.clock = self.clock.advance(step_ticks)
        out = [c for c in self.all_context if c.end > now and now > c.recorded_at and now.advance(self.horizon) > c.start]
        return out
