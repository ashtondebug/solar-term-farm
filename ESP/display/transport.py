"""UART transport for the TJC screen.

Nextion/TJC component commands are terminated by three 0xFF bytes.  Incoming
screen lines are newline-terminated ASCII.  The buffer is deliberately small:
a malformed/noisy line must not grow the heap without bound.
"""

MAX_BUFFER = 512


class UartTransport:
    def __init__(self, uart):
        self.uart = uart
        self.buffer = b""

    def read_lines(self):
        try:
            count = self.uart.any()
            if count:
                data = self.uart.read(count)
                if data:
                    self.buffer += data
        except Exception:
            return []
        if len(self.buffer) > MAX_BUFFER:
            self.buffer = b""
            return []
        lines = []
        while b"\n" in self.buffer:
            raw, self.buffer = self.buffer.split(b"\n", 1)
            text = raw.replace(b"\r", b"").decode("utf-8", "replace")
            if text:
                lines.append(text)
        return lines

    def send(self, command):
        if not command:
            return
        self.uart.write(command.encode("utf-8") + b"\xff\xff\xff")

    def close(self):
        try:
            self.uart.deinit()
        except Exception:
            pass
