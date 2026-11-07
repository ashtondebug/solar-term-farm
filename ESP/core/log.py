"""Small structured logger for the firmware.

MicroPython does not provide a full logging package on every build, so this
module keeps a bounded in-memory ring for diagnostics and writes to a sink
(stdout by default).  It never prints secrets; callers are responsible for
not passing them in.
"""

try:
    import sys
except ImportError:  # pragma: no cover - MicroPython always has sys
    sys = None

_LEVELS = {"debug": 10, "info": 20, "warn": 30, "error": 40}


class Logger:
    def __init__(self, name="agri", level="info", sink=None, max_lines=200):
        self.name = name
        self.level = _LEVELS.get(level, 20)
        self.sink = sink
        self.max_lines = max_lines
        self.lines = []

    def child(self, suffix):
        return Logger("%s.%s" % (self.name, suffix), level=self._level_name(), sink=self.sink)

    def _level_name(self):
        for name, value in _LEVELS.items():
            if value == self.level:
                return name
        return "info"

    def _log(self, level, message, *args):
        if _LEVELS[level] < self.level:
            return
        if args:
            try:
                message = message % args
            except Exception:
                message = "%s %s" % (message, args)
        line = "[%s] %s: %s" % (level.upper(), self.name, message)
        self.lines.append(line)
        if len(self.lines) > self.max_lines:
            del self.lines[0:max(1, self.max_lines // 4)]
        if self.sink is not None:
            try:
                self.sink(line)
            except Exception:
                pass
        elif sys is not None:
            try:
                sys.stdout.write(line + "\n")
            except Exception:
                pass

    def debug(self, message, *args):
        self._log("debug", message, *args)

    def info(self, message, *args):
        self._log("info", message, *args)

    def warn(self, message, *args):
        self._log("warn", message, *args)

    def error(self, message, *args):
        self._log("error", message, *args)

    def exception(self, message, exc):
        self.error("%s: %s", message, exc)

    def tail(self, count=20):
        return self.lines[-count:]
