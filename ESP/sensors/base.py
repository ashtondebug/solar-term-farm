"""Sensor primitives.

Drivers receive their bus (I2C/ADC) through the constructor.  They never
import ``machine``, which keeps the same code testable on CPython and makes
the hardware seam explicit in ``main.py``.
"""


class Reading:
    __slots__ = ("value", "unit", "valid", "ts", "error", "raw")

    def __init__(self, value, unit, valid, ts, error=None, raw=None):
        self.value = value
        self.unit = unit
        self.valid = bool(valid)
        self.ts = int(ts)
        self.error = error
        self.raw = raw

    def as_dict(self):
        return {
            "value": None if self.value is None else round(float(self.value), 3),
            "unit": self.unit,
            "valid": self.valid,
            "ts": self.ts,
            "error": self.error,
            "raw": self.raw,
        }

    def __repr__(self):
        return "Reading(value=%r, unit=%r, valid=%r, error=%r)" % (
            self.value,
            self.unit,
            self.valid,
            self.error,
        )


def is_stale(reading, now, max_age_s):
    if reading is None or not reading.valid:
        return True
    return (int(now) - int(reading.ts)) > max_age_s
