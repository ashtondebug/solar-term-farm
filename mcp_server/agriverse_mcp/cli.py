"""Command-line entry point for the AgriVerse MCP server."""

from __future__ import annotations

import argparse
import logging
import sys

from .config import Settings
from .device_client import DeviceClient
from .server import build_server
from .service import AgriVerseService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AgriVerse MCP server (runs on a PC, not on the ESP32)")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default=None,
        help="MCP transport; default comes from AGRI_MCP_TRANSPORT or stdio",
    )
    parser.add_argument("--host", default=None, help="HTTP bind address; default 127.0.0.1")
    parser.add_argument("--port", type=int, default=None, help="HTTP port; default 8765")
    parser.add_argument("--base-url", default=None, help="ESP32 base URL, e.g. http://192.168.153.234")
    parser.add_argument(
        "--allow-control",
        action="store_true",
        default=None,
        help="register pump/config control tools; also AGRI_ALLOW_CONTROL=1",
    )
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    if args.transport:
        settings = Settings(**{**settings.__dict__, "transport": args.transport})
    if args.host:
        settings = Settings(**{**settings.__dict__, "host": args.host})
    if args.port is not None:
        settings = Settings(**{**settings.__dict__, "port": args.port})
    if args.base_url:
        settings = Settings(**{**settings.__dict__, "base_url": args.base_url.rstrip("/")})
    if args.allow_control is not None:
        settings = Settings(**{**settings.__dict__, "allow_control": args.allow_control})

    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        settings.validate()
    except ValueError as exc:
        logging.getLogger("agriverse.mcp").error("%s", exc)
        return 2

    client = DeviceClient(settings.base_url, settings.pin, settings.timeout_s)
    service = AgriVerseService(client, settings.allow_control)
    mcp = build_server(service, host=settings.host, port=settings.port)

    logging.getLogger("agriverse.mcp").info(
        "starting AgriVerse MCP transport=%s base_url=%s control=%s",
        settings.transport,
        settings.base_url,
        settings.allow_control,
    )
    try:
        mcp.run(transport=settings.transport)
    except KeyboardInterrupt:
        return 0
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
