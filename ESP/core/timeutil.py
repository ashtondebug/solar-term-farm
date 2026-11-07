"""Time helpers shared by firmware and host tools.

MicroPython ports differ in their epoch: Unix ports use 1970-01-01 while some
bare-metal ports use 2000-01-01.  The API and browser always speak Unix
seconds, so this module detects the local epoch once and normalizes every
conversion.  Without this, syncing a 2026 browser clock on a 2000-epoch board
would display 2054 and compute the wrong solar term.
"""

import time

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _detect_epoch_offset():
    try:
        if time.gmtime(0)[0] == 2000:
            return 946684800  # seconds between 1970-01-01 and 2000-01-01
    except Exception:
        pass
    return 0


EPOCH_OFFSET = _detect_epoch_offset()


class Clock:
    def now(self):
        raise NotImplementedError

    def set_epoch(self, epoch):
        raise NotImplementedError

    @property
    def synced(self):
        return True


class SystemClock(Clock):
    """Wall clock backed by ``time.time`` and an optional machine RTC.

    ``now()`` always returns Unix seconds.  ``rtc`` is injected by the
    composition root so this module stays importable on CPython.
    """

    def __init__(self, rtc=None, offset_s=0):
        self.rtc = rtc
        self._offset = int(offset_s)
        self._synced = False

    def now(self):
        try:
            return int(time.time()) + EPOCH_OFFSET + self._offset
        except Exception:
            return self._offset

    def set_epoch(self, epoch):
        epoch = int(epoch)
        if self.rtc is not None:
            try:
                # The RTC setter expects a broken-down local date/time; the
                # tuple's weekday is 0=Monday on MicroPython.
                t = time.gmtime(epoch - EPOCH_OFFSET)
                self.rtc.datetime((t[0], t[1], t[2], t[6], t[3], t[4], t[5], 0))
            except Exception:
                self._offset = epoch - (int(time.time()) + EPOCH_OFFSET)
        else:
            self._offset = epoch - (int(time.time()) + EPOCH_OFFSET)
        self._synced = True

    @property
    def synced(self):
        return self._synced


def local_parts(epoch, offset_s):
    return time.gmtime(int(epoch) - EPOCH_OFFSET + int(offset_s))


def format_local(epoch, offset_s, with_zone=True):
    t = local_parts(epoch, offset_s)
    text = "%04d-%02d-%02dT%02d:%02d:%02d" % (
        t[0], t[1], t[2], t[3], t[4], t[5]
    )
    if with_zone:
        sign = "+" if offset_s >= 0 else "-"
        minutes = abs(int(offset_s)) // 60
        text += "%s%02d:%02d" % (sign, minutes // 60, minutes % 60)
    return text


def format_local_short(epoch, offset_s):
    t = local_parts(epoch, offset_s)
    return "%04d-%02d-%02d %02d:%02d" % (t[0], t[1], t[2], t[3], t[4])


def uptime_text(seconds):
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        return "%dd %02dh %02dm" % (days, hours, minutes)
    if hours:
        return "%dh %02dm" % (hours, minutes)
    if minutes:
        return "%dm %02ds" % (minutes, secs)
    return "%ds" % secs
