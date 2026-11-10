"""HTTP client for the AgriVerse device REST API."""

from __future__ import annotations

from typing import Any

import httpx


class DeviceError(Exception):
    """A device, network, or API error with a stable code."""

    def __init__(self, code: str, message: str, status: int | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status

    def __str__(self) -> str:
        return "%s: %s" % (self.code, self.message)


class DeviceClient:
    """Small typed wrapper around the device REST API.

    The MCP layer must never write GPIO directly.  Every control request goes
    through the device's ``/api/v1/irrigation/commands`` endpoint, so the
    IrrigationController keeps ownership of max-run, min-off, and fault logic.
    """

    def __init__(
        self,
        base_url: str,
        pin: str = "",
        timeout_s: float = 8.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.pin = pin
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout_s,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "DeviceClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _headers(self, write: bool) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if write and self.pin:
            headers["X-AgriVerse-Pin"] = self.pin
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        write: bool = False,
    ) -> Any:
        try:
            response = self._client.request(
                method,
                path,
                json=json,
                params=params,
                headers=self._headers(write),
            )
        except httpx.TimeoutException as exc:
            raise DeviceError("DEVICE_TIMEOUT", "device did not answer in time") from exc
        except httpx.HTTPError as exc:
            raise DeviceError("DEVICE_UNREACHABLE", "cannot reach device: %s" % exc) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise DeviceError(
                "BAD_RESPONSE",
                "device returned non-JSON (HTTP %s)" % response.status_code,
                response.status_code,
            ) from exc

        if not isinstance(payload, dict):
            raise DeviceError("BAD_RESPONSE", "device returned an invalid envelope", response.status_code)
        if not payload.get("ok"):
            error = payload.get("error") or {}
            raise DeviceError(
                str(error.get("code") or "DEVICE_ERROR"),
                str(error.get("message") or "device request failed"),
                response.status_code,
            )
        return payload.get("data")

    # ------------------------------------------------------------------ reads
    def state(self) -> dict[str, Any]:
        return self.request("GET", "/api/v1/state")

    def history(self, range_name: str = "12h") -> dict[str, Any]:
        return self.request("GET", "/api/v1/history", params={"range": range_name})

    def plant_profiles(self) -> dict[str, Any]:
        return self.request("GET", "/api/v1/plant-profiles")

    def config(self) -> dict[str, Any]:
        return self.request("GET", "/api/v1/config")

    def health(self) -> dict[str, Any]:
        return self.request("GET", "/api/v1/health")

    # ----------------------------------------------------------------- writes
    def command(self, action: str, request_id: str) -> dict[str, Any]:
        return self.request(
            "POST",
            "/api/v1/irrigation/commands",
            json={"action": action, "request_id": request_id},
            write=True,
        )

    def update_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("PUT", "/api/v1/config", json=payload, write=True)

    def import_profiles(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request(
            "POST",
            "/api/v1/plant-profiles/import",
            json=payload,
            write=True,
        )
