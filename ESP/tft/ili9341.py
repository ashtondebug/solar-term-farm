"""Minimal ILI9341 240x320 SPI driver.

No full-screen RGB565 framebuffer is allocated; the display task sends one
small monochrome line tile at a time. This keeps RAM usage safe on the ESP32-S3.
"""

import time

from machine import Pin


class ILI9341:
    def __init__(self, spi, cs, dc, rst, width=240, height=320, rotation=0):
        self.spi = spi
        self.cs = Pin(cs, Pin.OUT, value=1)
        self.dc = Pin(dc, Pin.OUT, value=1)
        self.rst = Pin(rst, Pin.OUT, value=1)
        self.width = width
        self.height = height
        self.rotation = rotation
        self.reset()
        self.init_display()

    def reset(self):
        self.rst.value(0)
        time.sleep_ms(20)
        self.rst.value(1)
        time.sleep_ms(120)

    def _cmd(self, cmd, data=None):
        self.cs.value(0)
        self.dc.value(0)
        self.spi.write(bytes((cmd,)))
        if data:
            self.dc.value(1)
            self.spi.write(bytes(data))
        self.cs.value(1)

    def init_display(self):
        self._cmd(0x01)  # software reset
        time.sleep_ms(120)
        self._cmd(0x11)  # sleep out
        time.sleep_ms(120)
        for cmd, data in (
            (0xCF, (0x00, 0xC1, 0x30)),
            (0xED, (0x64, 0x03, 0x12, 0x81)),
            (0xE8, (0x85, 0x00, 0x78)),
            (0xCB, (0x39, 0x2C, 0x00, 0x34, 0x02)),
            (0xF7, (0x20,)),
            (0xEA, (0x00, 0x00)),
            (0xC0, (0x23,)),
            (0xC1, (0x10,)),
            (0xC5, (0x3E, 0x28)),
            (0xC7, (0x86,)),
            (0x36, ({0: 0x48, 1: 0x28, 2: 0x88, 3: 0xE8}.get(self.rotation, 0x48),)),
            (0x3A, (0x55,)),
            (0xB1, (0x00, 0x18)),
            (0xB6, (0x08, 0x82, 0x27)),
            (0xF2, (0x00,)),
            (0x26, (0x01,)),
            (0xE0, (0x0F, 0x31, 0x2B, 0x0C, 0x0E, 0x08, 0x4E,
                    0xF1, 0x37, 0x07, 0x10, 0x03, 0x0E, 0x09, 0x00)),
            (0xE1, (0x00, 0x0E, 0x14, 0x03, 0x11, 0x07, 0x31,
                    0xC1, 0x48, 0x08, 0x0F, 0x0C, 0x31, 0x36, 0x0F)),
            (0x11, None),
            (0x29, None),
        ):
            self._cmd(cmd, data)
            if cmd == 0x11:
                time.sleep_ms(120)
            elif cmd == 0x29:
                time.sleep_ms(20)

    def set_window(self, x0, y0, x1, y1):
        self._cmd(0x2A, (x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF))
        self._cmd(0x2B, (y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF))
        self._cmd(0x2C)

    def fill_rect(self, x, y, w, h, color):
        if w <= 0 or h <= 0:
            return
        self.set_window(x, y, x + w - 1, y + h - 1)
        hi = (color >> 8) & 0xFF
        lo = color & 0xFF
        line = bytes((hi, lo)) * w
        self.dc.value(1)
        self.cs.value(0)
        for _ in range(h):
            self.spi.write(line)
        self.cs.value(1)

    def fill(self, color):
        self.fill_rect(0, 0, self.width, self.height, color)

    def draw_mono(self, x, y, w, h, fg, bg, framebuf):
        self.set_window(x, y, x + w - 1, y + h - 1)
        self.dc.value(1)
        self.cs.value(0)
        line = bytearray(w * 2)
        fg_hi, fg_lo = (fg >> 8) & 0xFF, fg & 0xFF
        bg_hi, bg_lo = (bg >> 8) & 0xFF, bg & 0xFF
        for row in range(h):
            for col in range(w):
                if framebuf.pixel(col, row):
                    line[col * 2] = fg_hi
                    line[col * 2 + 1] = fg_lo
                else:
                    line[col * 2] = bg_hi
                    line[col * 2 + 1] = bg_lo
            self.spi.write(line)
        self.cs.value(1)
