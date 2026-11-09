"""Line protocol between the TJC screen and the ESP32.

The screen sends short ASCII lines.  The firmware replies by updating named
HMI components (``t_temp.txt="..."``), not by sending JSON.  Keeping this
module pure makes the parser testable without hardware.
"""

MAX_LINE = 160
PAGES = ("boot", "overview", "environment", "irrigation", "settings", "wifi")


def _split(line, count=-1):
    return line.split("|", count)


def parse_line(line):
    """Return a command dict, or None for an empty line.

    Raises ValueError for malformed commands.  The caller decides whether the
    command needs a PIN; parsing never performs I/O.
    """
    if line is None:
        return None
    line = line.strip()
    if not line:
        return None
    if len(line) > MAX_LINE:
        raise ValueError("LINE_TOO_LONG")
    parts = _split(line)
    command = parts[0].upper()
    if command == "AUTH":
        if len(parts) != 2 or not parts[1]:
            raise ValueError("BAD_AUTH")
        return {"cmd": "AUTH", "pin": parts[1]}
    if command == "PING":
        return {"cmd": "PING"}
    if command == "PAGE":
        if len(parts) != 2 or parts[1] not in PAGES:
            raise ValueError("BAD_PAGE")
        return {"cmd": "PAGE", "page": parts[1]}
    if command == "CMD":
        if len(parts) < 2 or parts[1] not in ("start", "stop"):
            raise ValueError("BAD_ACTION")
        return {"cmd": "CMD", "action": parts[1]}
    if command == "MODE":
        if len(parts) != 2 or parts[1] not in ("auto", "manual"):
            raise ValueError("BAD_MODE")
        return {"cmd": "MODE", "mode": parts[1]}
    if command == "SET":
        if len(parts) != 3 or parts[1] not in ("soil_threshold",):
            raise ValueError("BAD_SETTING")
        try:
            value = float(parts[2])
        except ValueError:
            raise ValueError("BAD_SETTING_VALUE")
        if value < 0 or value > 100:
            raise ValueError("BAD_SETTING_VALUE")
        return {"cmd": "SET", "key": parts[1], "value": value}
    if command == "WIFI":
        if len(parts) < 2:
            raise ValueError("BAD_WIFI")
        action = parts[1].upper()
        if action == "SCAN":
            return {"cmd": "WIFI", "action": "SCAN"}
        if action == "CONNECT":
            if len(parts) < 3 or not parts[2]:
                raise ValueError("WIFI_SSID_REQUIRED")
            # Keep '|' characters in the password rather than truncating it.
            rest = line.split("|", 3)
            password = rest[3] if len(rest) == 4 else ""
            return {"cmd": "WIFI", "action": "CONNECT", "ssid": rest[2], "password": password}
        raise ValueError("BAD_WIFI")
    if command == "PIN":
        if len(parts) == 2 and parts[1].upper() == "SHOW":
            return {"cmd": "PIN", "action": "SHOW"}
        raise ValueError("BAD_PIN")
    raise ValueError("UNKNOWN_COMMAND")


def escape_text(value):
    text = str(value)
    text = text.replace("\\", "\\\\").replace('"', "'")
    text = text.replace("\r", " ").replace("\n", " ").replace("\xff", " ")
    return text


def text_command(component, value):
    return '%s.txt="%s"' % (component, escape_text(value))


def number_command(component, value):
    return "%s.val=%d" % (component, int(value))


def page_command(page):
    if page not in PAGES:
        raise ValueError("BAD_PAGE")
    return "page %s" % page
