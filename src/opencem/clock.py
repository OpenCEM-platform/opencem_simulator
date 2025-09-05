from dataclasses import dataclass
import numpy as np
import pandas as pd
import time

@dataclass(frozen=True)
class Clock:
    ticks: int
    RES: int = 10**9

    @staticmethod
    def now(res: int = 10**9) -> "Clock":
        return Clock(ticks = time.time_ns() * res // 10**9, RES = res)

    @staticmethod
    def from_string(s: str, res: int = 10**9) -> "Clock":
        return Clock(ticks = pd.Timestamp(s).value * res // 10**9, RES = res)

    @staticmethod
    def from_seconds(s: float, *, res: int = 10**9) -> "Clock":
        ticks = round( s * res )
        return Clock(ticks = ticks, RES = res)

    def to_microseconds(self) -> float:
        return (self.ticks * 10**6) / self.RES

    def to_seconds(self) -> float:
        return self.ticks / self.RES

    @staticmethod
    def difference_hours(from_clock: "Clock", to_clock: "Clock") -> float:
        assert from_clock.RES == to_clock.RES
        return ((to_clock.ticks - from_clock.ticks) / to_clock.RES) / (60 * 60)

    def advance(self, step_ticks: int) -> "Clock":
        return Clock(ticks = self.ticks + step_ticks, RES = self.RES)

    def advance_seconds(self, seconds: float) -> "Clock":
        return self.advance(step_ticks = round(seconds * self.RES))

    def align(self, ticks_per_step: int) -> "Clock":
        aligned_ticks = round(self.ticks / ticks_per_step) * ticks_per_step
        return Clock(ticks = aligned_ticks, RES = self.RES)

    def to_numpy_datetime64(self) -> "np.datetime64":
        ns = self.ticks * (10**9 // self.RES)
        return np.datetime64(ns, "ns")

    def __str__(self) -> str:
        return str(self.to_numpy_datetime64())

    def __gt__(self, other: "Clock") -> bool:
        return self.ticks > other.ticks
