"""Always-on 240x320 portrait dashboard for SolarTerm Farm.

Only ASCII text is drawn on the TFT; the built-in font has no Chinese glyphs.
The static layout is painted once, then only changed values are repainted.
"""

import asyncio

import framebuf


TERM_EN = (
    "Start of Spring", "Rain Water", "Awakening", "Spring Equinox",
    "Clear and Bright", "Grain Rain", "Start of Summer", "Grain Full",
    "Grain in Ear", "Summer Solstice", "Minor Heat", "Major Heat",
    "Start of Autumn", "End of Heat", "White Dew", "Autumn Equinox",
    "Cold Dew", "Frost Descent", "Start of Winter", "Minor Snow",
    "Major Snow", "Winter Solstice", "Minor Cold", "Major Cold",
)
TERM_DATES = (
    "FEB 3-5", "FEB 18-20", "MAR 5-7", "MAR 20-22",
    "APR 4-6", "APR 19-21", "MAY 5-7", "MAY 20-22",
    "JUN 5-7", "JUN 21-22", "JUL 6-8", "JUL 22-24",
    "AUG 7-9", "AUG 22-24", "SEP 7-9", "SEP 22-24",
    "OCT 8-9", "OCT 23-24", "NOV 7-8", "NOV 22-23",
    "DEC 6-8", "DEC 21-23", "JAN 5-7", "JAN 20-21",
)
SEASON_EN = ("SPRING", "SUMMER", "AUTUMN", "WINTER")


class TftDisplay:
    WIDTH = 240
    HEIGHT = 320
    BG = 0x0B1712
    HEADER = 0x173D32
    CARD = 0x12271F
    WHITE = 0xF4FAF6
    MUTED = 0x9EB8A8
    GREEN = 0x74C69D
    GOLD = 0xE6A100
    RED = 0xC65C4E

    def __init__(self, tft, state, clock, logger):
        self.tft = tft
        self.state = state
        self.clock = clock
        self.logger = logger
        self._tile = bytearray(self.WIDTH * 8 // 8)
        self._fb = framebuf.FrameBuffer(self._tile, self.WIDTH, 8, framebuf.MONO_HLSB)
        self._last = {}
        self._ready = False
        self._last_term = None

    @staticmethod
    def _fmt(value, digits=1):
        if value is None:
            return "--"
        try:
            return ("%." + str(digits) + "f") % float(value)
        except Exception:
            return "--"

    @staticmethod
    def _term_info(term):
        try:
            index = int(term.get("index", -1))
        except Exception:
            index = -1
        if 0 <= index < len(TERM_EN):
            return TERM_EN[index], SEASON_EN[index // 6], TERM_DATES[index], index
        return "SOLAR TERM", "----", "----", -1

    def _box_text(self, text, x, y, w, fg, bg):
        if w > self.WIDTH:
            w = self.WIDTH
        if w <= 0:
            return
        self._fb.fill(0)
        self._fb.text(str(text), 0, 0, 1)
        self.tft.draw_mono(x, y, w, 8, fg, bg, self._fb)

    def _card(self, x, y, w, h):
        self.tft.fill_rect(x, y, w, h, self.CARD)

    def _clock_text(self, snapshot):
        local = (snapshot.get("device") or {}).get("now_local") or ""
        return local[11:16] if len(local) >= 16 else "--:--"

    def _draw_static(self, term):
        name, season, _date, _idx = self._term_info(term)
        self.tft.fill(self.BG)
        self.tft.fill_rect(0, 0, self.WIDTH, 40, self.HEADER)
        self._box_text("SolarTerm Farm", 10, 7, 120, self.WHITE, self.HEADER)
        self._box_text(name + " / " + season, 10, 23, 210, self.GOLD, self.HEADER)

        self._card(8, 48, 108, 38)
        self._card(124, 48, 108, 38)
        self._card(8, 92, 108, 38)
        self._card(124, 92, 108, 38)
        self._card(8, 136, 108, 38)
        self._card(124, 136, 108, 38)
        self._card(8, 180, 224, 88)

        self._box_text("AIR TEMP", 14, 53, 96, self.MUTED, self.CARD)
        self._box_text("AIR HUM", 130, 53, 96, self.MUTED, self.CARD)
        self._box_text("SOIL", 14, 97, 96, self.MUTED, self.CARD)
        self._box_text("LIGHT", 130, 97, 96, self.MUTED, self.CARD)
        self._box_text("PUMP", 14, 141, 96, self.MUTED, self.CARD)
        self._box_text("MODE", 130, 141, 96, self.MUTED, self.CARD)
        self._box_text("SOLAR TERM", 14, 186, 120, self.MUTED, self.CARD)
        self._box_text("SolarTerm Farm LOCAL", 8, 300, 180, self.MUTED, self.BG)
        self._ready = True

    def _redraw_term(self, term):
        name, season, date_hint, _idx = self._term_info(term)
        self._box_text(name + " / " + season, 10, 23, 210, self.GOLD, self.HEADER)
        self._box_text(name, 14, 200, 110, self.GOLD, self.CARD)
        self._box_text(date_hint, 130, 200, 94, self.MUTED, self.CARD)
        self._box_text("TIP: CHECK SOIL, LIGHT, WATER", 14, 218, 212, self.WHITE, self.CARD)
        self._box_text("SEASONAL FARMING", 14, 230, 212, self.MUTED, self.CARD)

    def _value(self, key, text, x, y, w, fg, bg=None):
        bg = self.CARD if bg is None else bg
        if self._last.get(key) == text:
            return
        self._box_text(text, x, y, w, fg, bg)
        self._last[key] = text

    def render(self, now):
        snapshot = self.state.snapshot(now)
        sensors = snapshot.get("sensors") or {}
        irrigation = snapshot.get("irrigation") or {}
        term = snapshot.get("solar_term") or {}
        suitability = snapshot.get("suitability") or {}
        _name, _season, _date, index = self._term_info(term)

        if not self._ready:
            self._draw_static(term)
            self._redraw_term(term)
            self._last_term = index

        self._value("time", self._clock_text(snapshot), 182, 7, 50, self.WHITE, self.HEADER)
        self._value("temp", self._fmt((sensors.get("air_temp") or {}).get("value"), 1) + " C", 14, 67, 96, self.WHITE)
        self._value("hum", self._fmt((sensors.get("air_humidity") or {}).get("value"), 0) + " %", 130, 67, 96, self.WHITE)
        self._value("soil", self._fmt((sensors.get("soil") or {}).get("value"), 0) + " %", 14, 111, 96, self.GOLD)
        self._value("light", self._fmt((sensors.get("light") or {}).get("value"), 0) + " lx", 130, 111, 96, self.GOLD)

        pump = "ON" if irrigation.get("pump") else "OFF"
        self._value("pump", pump, 14, 155, 96, self.GREEN if pump == "ON" else self.RED)
        self._value("mode", str(irrigation.get("mode", "auto")).upper(), 130, 155, 96, self.WHITE)

        if index != self._last_term:
            self._redraw_term(term)
            self._last_term = index

        score = suitability.get("score")
        self._value(
            "score",
            "SUIT " + (("%s/100" % score) if score is not None else "--"),
            14, 258, 180,
            self.GREEN if score is not None and score >= 60 else self.GOLD,
        )

    async def run(self):
        while True:
            try:
                self.render(self.clock.now())
            except Exception as exc:
                self.logger.warn("tft refresh failed: %s", exc)
            await asyncio.sleep(5)
