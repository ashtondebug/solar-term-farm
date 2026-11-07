"""Bounded in-memory irrigation history (last N runs)."""


class IrrigationHistory:
    def __init__(self, limit=50):
        self.limit = limit
        self.records = []
        self.current = None

    def start(self, ts, trigger):
        if self.current is not None:
            self.stop(ts, "replaced")
        self.current = {
            "start_ts": int(ts),
            "trigger": trigger,
            "end_ts": None,
            "duration_s": 0,
            "stop_reason": None,
        }

    def stop(self, ts, reason):
        if self.current is None:
            return None
        record = self.current
        record["end_ts"] = int(ts)
        record["duration_s"] = max(0, int(ts) - int(record["start_ts"]))
        record["stop_reason"] = reason
        self.records.append(record)
        if len(self.records) > self.limit:
            del self.records[0 : len(self.records) - self.limit]
        self.current = None
        return record

    def recent(self, count=10):
        items = list(self.records)
        if self.current is not None:
            running = dict(self.current)
            running["end_ts"] = None
            running["duration_s"] = None
            running["stop_reason"] = None
            items.append(running)
        return items[-count:][::-1]

    def today_count(self, start_ts):
        return len([r for r in self.records if r.get("start_ts", 0) >= start_ts])
