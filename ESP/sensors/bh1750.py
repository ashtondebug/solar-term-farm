"""BH1750 ambient-light sensor (I2C, continuous high-resolution mode)."""

import time

from sensors.base import Reading


class BH1750:
    name = "light"
    unit = "lx"

    def __init__(self, i2c, address=0x23, sleep=None):
        self.i2c = i2c
        self.address = address
        self._sleep = sleep or time.sleep

    def read(self, now):
        try:
            self.i2c.writeto(self.address, b"\x10")
            self._sleep(0.12)
            data = self.i2c.readfrom(self.address, 2)
        except Exception as exc:
            return Reading(None, self.unit, False, now, "i2c_error: %s" % exc)
        if len(data) != 2:
            return Reading(None, self.unit, False, now, "short_read")
        lux = ((data[0] << 8) | data[1]) / 1.2
        if lux < 0 or lux > 100000:
            return Reading(None, self.unit, False, now, "lux_out_of_range")
        return Reading(lux, self.unit, True, now, None)
