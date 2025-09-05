import sqlite3
from clock import Clock
from collections.abc import Sequence
import numbers
from typing import Any, Optional
from interfaces import Battery, BatteryStepMode, BatteryStepInput, BatteryStepResult, PowerSource, PowerSourceStepResult, Load, LoadStepResult, Grid, GridStepInput, GridStepResult, PowerSource, PowerSourceStepResult, Inverter, InverterStepInput, InverterStepResult

def fetch_around_unix_ts(conn: sqlite3.Connection, table: str, inverter: int, ts_seconds: float | int):
    """
    table: table name
    ts_seconds: unix timestamp (UTC)
    """
    conn.row_factory = sqlite3.Row
    if not table.isidentifier():
        raise ValueError(f"Unsafe table name: {table}")

    sql = f"""
    WITH params(ts) AS (VALUES (?)),
    exact AS (
      SELECT 'exact' AS kind, m.*
      FROM {table} m, params
      WHERE m.inverter = ?
        AND m.read_ts = params.ts
    ),
    prev AS (
      SELECT 'prev' AS kind, m.*
      FROM {table} m, params
      WHERE m.inverter = ?
        AND m.read_ts < params.ts
      ORDER BY m.read_ts DESC
      LIMIT 1
    ),
    next AS (
      SELECT 'next' AS kind, m.*
      FROM {table} m, params
      WHERE m.inverter = ?
        AND m.read_ts > params.ts
      ORDER BY m.read_ts ASC
      LIMIT 1
    )
    SELECT * FROM exact
    UNION ALL
    SELECT * FROM prev WHERE NOT EXISTS (SELECT 1 FROM exact)
    UNION ALL
    SELECT * FROM next WHERE NOT EXISTS (SELECT 1 FROM exact);
    """

    cur = conn.execute(sql, (ts_seconds, inverter, inverter, inverter))
    rows = cur.fetchall()
    return rows

def interpolate_row(rows: Sequence[sqlite3.Row], ts: float) -> dict[str, Any]:
    """
    Given rows from fetch_around_unix_ts(...), always return one row.
    - If exact row exists, return it as dict.
    - If prev+next, interpolate numeric columns at ts.
    - If only one row (prev or next), return that row.
    """
    if not rows:
        raise ValueError("No rows returned — table may be empty?")

    rows_dict = [{k: r[k] for k in r.keys()} for r in rows]

    for r in rows_dict:
        if r["kind"] == "exact":
            return r

    prev = next_ = None
    for r in rows_dict:
        if r["kind"] == "prev":
            prev = r
        elif r["kind"] == "next":
            next_ = r

    if prev and next_:
        t0, t1 = prev["read_ts"], next_["read_ts"]
        if t1 == t0:
            return prev
        alpha = (ts - t0) / (t1 - t0)

        result = {"kind": "interp", "read_ts": ts, "inverter": prev["inverter"]}
        for key in prev.keys():
            if key in ("kind", "read_ts", "inverter"):
                continue
            v0, v1 = prev[key], next_[key]
            if (isinstance(v0, numbers.Number) and
                isinstance(v1, numbers.Number) and
                isinstance(v0, (int, float)) and isinstance(v1, (int, float))):
                result[key] = v0 + alpha * (v1 - v0)
            else:
                result[key] = v0
        return result
    return prev or next_

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
