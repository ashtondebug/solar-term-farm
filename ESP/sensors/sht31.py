"""SHT31 temperature/humidity sensor (I2C, single-shot high repeatability)."""

import time

from sensors.base import Reading

CRC_POLY = 0x31


def crc8(data):
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ CRC_POLY) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def decode(raw_temp, raw_humidity):
    temperature = -45.0 + 175.0 * raw_temp / 65535.0
    humidity = 100.0 * raw_humidity / 65535.0
    return temperature, humidity


class SHT31:
    name = "air"
    unit = "C/%"

    def __init__(self, i2c, address=0x44, sleep=None):
        self.i2c = i2c
        self.address = address
        self._sleep = sleep or time.sleep
        self.last_raw = None

    def read(self, now):
        try:
            self.i2c.writeto(self.address, b"\x2c\x06")
            self._sleep(0.02)
            data = self.i2c.readfrom(self.address, 6)
        except Exception as exc:
            return self._invalid(now, "i2c_error: %s" % exc)

        if len(data) != 6:
            return self._invalid(now, "short_read")
        if crc8(data[0:2]) != data[2] or crc8(data[3:5]) != data[5]:
            return self._invalid(now, "crc_error")

        raw_temp = (data[0] << 8) | data[1]
        raw_humidity = (data[3] << 8) | data[4]
        self.last_raw = (raw_temp, raw_humidity)
        temperature, humidity = decode(raw_temp, raw_humidity)
        if temperature < -40 or temperature > 125:
            return self._invalid(now, "temperature_out_of_range")
        if humidity < 0 or humidity > 100:
            return self._invalid(now, "humidity_out_of_range")
        return (
            Reading(temperature, "C", True, now, None),
            Reading(humidity, "%", True, now, None),
        )

    @staticmethod
    def _invalid(now, error):
        return (
            Reading(None, "C", False, now, error),
            Reading(None, "%", False, now, error),
        )
