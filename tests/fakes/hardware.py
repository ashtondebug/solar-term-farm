"""Small hardware fakes for host tests."""


class FakePin:
    def __init__(self, value=0):
        self._value = int(value)
        self.writes = []

    def value(self, new_value=None):
        if new_value is None:
            return self._value
        self._value = int(new_value)
        self.writes.append(self._value)
        return None


class FakeADC:
    def __init__(self, value=0):
        self.value = int(value)

    def read_u16(self):
        return self.value


class FakeI2C:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.writes = []

    def writeto(self, address, data):
        self.writes.append((address, bytes(data)))

    def readfrom(self, address, length):
        if not self.responses:
            raise OSError("no fake response")
        return self.responses.pop(0)


class FakeClock:
    synced = True

    def __init__(self, now=1700000000):
        self.t = int(now)

    def now(self):
        return self.t

    def set_epoch(self, epoch):
        self.t = int(epoch)

    def advance(self, seconds):
        self.t += int(seconds)
