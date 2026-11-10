"""Recovering I2C proxy for the SHT31/BH1750 shared bus.

The ESP32 SoftI2C implementation can raise ETIMEDOUT when a slave holds SDA low
after a glitch.  A normal ``SoftI2C`` re-init does not always release the bus;
clocking SCL nine times and issuing a STOP does.  The proxy retries one read or
write after recovery so a single bus glitch does not poison both sensors.
"""

import time

import machine


class RecoveringI2C:
    def __init__(self, scl, sda, freq=100000, logger=None):
        self.scl = int(scl)
        self.sda = int(sda)
        self.freq = int(freq)
        self.logger = logger
        self.bus = self._new_bus()

    def _new_bus(self):
        return machine.SoftI2C(
            scl=machine.Pin(self.scl),
            sda=machine.Pin(self.sda),
            freq=self.freq,
        )

    def recover(self):
        if self.logger:
            self.logger.warn("i2c bus recovery: clocking SCL and reinitializing")
        try:
            scl = machine.Pin(self.scl, machine.Pin.OPEN_DRAIN, machine.Pin.PULL_UP)
            sda = machine.Pin(self.sda, machine.Pin.OPEN_DRAIN, machine.Pin.PULL_UP)
            scl.value(1)
            sda.value(1)
            time.sleep_us(5)
            # Nine clocks let a slave finish a stuck byte.
            for _ in range(9):
                scl.value(0)
                time.sleep_us(5)
                scl.value(1)
                time.sleep_us(5)
            # STOP: SDA low while SCL high, then release SDA.
            sda.value(0)
            time.sleep_us(5)
            scl.value(1)
            time.sleep_us(5)
            sda.value(1)
            time.sleep_us(5)
            if sda.value() != 1 and self.logger:
                self.logger.warn("i2c recovery: SDA still low after STOP")
        except Exception as exc:
            if self.logger:
                self.logger.warn("i2c recovery failed: %s", exc)
        finally:
            try:
                self.bus = self._new_bus()
            except Exception as exc:
                if self.logger:
                    self.logger.warn("i2c reinit failed: %s", exc)

    @staticmethod
    def _recoverable(exc):
        text = str(exc).upper()
        return isinstance(exc, OSError) and (
            getattr(exc, "errno", None) in (5, 110, 116)
            or "ETIMEDOUT" in text
            or "EIO" in text
        )

    def _call(self, method, *args, **kwargs):
        try:
            return getattr(self.bus, method)(*args, **kwargs)
        except OSError as exc:
            if not self._recoverable(exc):
                raise
            self.recover()
            return getattr(self.bus, method)(*args, **kwargs)

    # The sensor drivers only need these methods.
    def readfrom(self, address, nbytes):
        return self._call("readfrom", address, nbytes)

    def writeto(self, address, data):
        return self._call("writeto", address, data)

    def readfrom_mem(self, address, memaddr, nbytes):
        return self._call("readfrom_mem", address, memaddr, nbytes)

    def writeto_mem(self, address, memaddr, data):
        return self._call("writeto_mem", address, memaddr, data)

    def scan(self):
        return self._call("scan")
