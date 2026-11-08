"""HW-390 V2.0 capacitive soil-moisture sensor on an ADC pin.

The sensor is ratiometric enough for a two-point calibration: record a dry
air/soil sample and a fully wet sample, then map raw counts linearly between
them.  Raw counts are never reported as a moisture percentage.
"""

from core.validation import clamp, is_number
from sensors.base import Reading

MIN_SPAN = 500
ADC_MAX = 65535


def validate_calibration(dry, wet):
    if not is_number(dry) or not is_number(wet):
        return "uncalibrated"
    if dry < 0 or dry > ADC_MAX or wet < 0 or wet > ADC_MAX:
        return "calibration_out_of_range"
    if abs(dry - wet) < MIN_SPAN:
        return "calibration_span_too_small"
    return None


def percent_from_raw(raw, dry, wet):
    """Return (percent, error).  Handles either endpoint ordering."""
    error = validate_calibration(dry, wet)
    if error:
        return None, error
    if not is_number(raw) or raw < 0 or raw > ADC_MAX:
        return None, "adc_out_of_range"
    span = dry - wet
    if span > 0:
        percent = (dry - raw) * 100.0 / span
    else:
        percent = (raw - dry) * 100.0 / (-span)
    return clamp(percent, 0.0, 100.0), None


class SoilSensor:
    name = "soil"
    unit = "%"

    def __init__(self, adc, get_calibration, clock):
        self.adc = adc
        self.get_calibration = get_calibration
        self.clock = clock
        self.last_raw = None

    def read_raw(self):
        reader = getattr(self.adc, "read_u16", None)
        if reader is not None:
            return reader()
        # Some ports expose a 12-bit read(); normalize to the 16-bit scale.
        return self.adc.read() * 16

    def read(self, now):
        try:
            raw = self.read_raw()
            self.last_raw = raw
        except Exception as exc:
            return Reading(None, self.unit, False, now, "adc_error: %s" % exc)
        calibration = self.get_calibration() or {}
        percent, error = percent_from_raw(
            raw, calibration.get("soil_dry"), calibration.get("soil_wet")
        )
        if error:
            return Reading(None, self.unit, False, now, error, raw=raw)
        return Reading(percent, self.unit, True, now, None, raw=raw)
