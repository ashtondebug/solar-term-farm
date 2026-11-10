"""FastMCP server exposing AgriVerse device capabilities.

Run this on the Windows PC, not on the ESP32.  The ESP32 remains the owner of
the relay and of the irrigation safety envelope.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from .device_client import DeviceClient, DeviceError
from .service import (
    CONFIRM_IMPORT,
    CONFIRM_MODE,
    CONFIRM_PROFILE,
    CONFIRM_START,
    CONFIRM_THRESHOLD,
    AgriVerseService,
    ServiceError,
)


def _fail(exc: Exception) -> None:
    if isinstance(exc, (ServiceError, DeviceError)):
        raise ToolError(str(exc)) from exc
    raise exc


def build_server(service: AgriVerseService | None = None, host: str = "127.0.0.1", port: int = 8765) -> FastMCP:
    service = service or AgriVerseService(DeviceClient("http://192.168.153.234"))
    mcp = FastMCP(
        "AgriVerse",
        instructions=(
            "AgriVerse 智能农业设备。读取传感器、适宜度、节气与灌溉状态；"
            "控制工具仅在 AGRI_ALLOW_CONTROL=1 时注册。"
            "启泵前先读取状态，启动后必须能随时 stop_irrigation。"
            "不要把设备返回值当作建议；以真实传感器读数为准。"
        ),
        host=host,
        port=port,
    )

    # ------------------------------------------------------------------ reads
    @mcp.tool(
        name="get_environment",
        description="读取空气温度、空气湿度、土壤湿度和光照强度；包含单位、有效性、数据年龄和 stale 标记。",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )
    def get_environment() -> dict[str, Any]:
        try:
            return service.get_environment()
        except Exception as exc:  # noqa: BLE001 - converted to MCP tool error
            _fail(exc)

    @mcp.tool(
        name="get_sensors",
        description="读取全部传感器明细，包括原始值、单位、时间戳、age_s、valid 和 error。",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )
    def get_sensors() -> dict[str, Any]:
        try:
            return service.get_sensors()
        except Exception as exc:
            _fail(exc)

    @mcp.tool(
        name="get_sensor_status",
        description="检查所有传感器是否有效且未过期；返回 all_ok 和每个传感器的状态。",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )
    def get_sensor_status() -> dict[str, Any]:
        try:
            return service.get_sensor_status()
        except Exception as exc:
            _fail(exc)

    @mcp.tool(
        name="get_suitability",
        description="读取当前植物环境适宜度、评分分量、当前档案和阶段。",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )
    def get_suitability() -> dict[str, Any]:
        try:
            return service.get_suitability()
        except Exception as exc:
            _fail(exc)

    @mcp.tool(
        name="get_solar_term",
        description="读取设备当前二十四节气、季节、时间和设备时间同步状态。",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )
    def get_solar_term() -> dict[str, Any]:
        try:
            return service.get_solar_term()
        except Exception as exc:
            _fail(exc)

    @mcp.tool(
        name="get_irrigation_status",
        description="读取水泵、模式、剩余运行时间、阈值、故障和最近灌溉记录。",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )
    def get_irrigation_status() -> dict[str, Any]:
        try:
            return service.get_irrigation_status()
        except Exception as exc:
            _fail(exc)

    @mcp.tool(
        name="get_history",
        description="读取环境历史点；range 可为 12h、24h 或 7d。",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )
    def get_history(range_name: str = "12h") -> dict[str, Any]:
        try:
            return service.get_history(range_name)
        except Exception as exc:
            _fail(exc)

    @mcp.tool(
        name="get_irrigation_history",
        description="读取最近灌溉动作记录，limit 范围 1–50。",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )
    def get_irrigation_history(limit: int = 10) -> dict[str, Any]:
        try:
            return service.get_irrigation_history(limit)
        except Exception as exc:
            _fail(exc)

    @mcp.tool(
        name="get_plant_profiles",
        description="列出设备内置和导入的植物档案以及可选生长阶段。",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )
    def get_plant_profiles() -> dict[str, Any]:
        try:
            return service.get_plant_profiles()
        except Exception as exc:
            _fail(exc)

    @mcp.tool(
        name="get_config",
        description="读取公开配置；PIN、密码、Token 已脱敏。",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )
    def get_config() -> dict[str, Any]:
        try:
            return service.get_config()
        except Exception as exc:
            _fail(exc)

    @mcp.tool(
        name="get_health",
        description="读取设备轻量健康信息、版本和运行时间。",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )
    def get_health() -> dict[str, Any]:
        try:
            return service.get_health()
        except Exception as exc:
            _fail(exc)

    @mcp.tool(
        name="diagnose",
        description="汇总传感器过期、网络离线、灌溉故障等诊断信息。",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )
    def diagnose() -> dict[str, Any]:
        try:
            return service.diagnose()
        except Exception as exc:
            _fail(exc)

    # ---------------------------------------------------------------- controls
    @mcp.tool(
        name="stop_irrigation",
        description="立即停止水泵。该工具始终可用，不需要确认。",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True),
    )
    def stop_irrigation(request_id: str | None = None) -> dict[str, Any]:
        try:
            return service.stop_irrigation(request_id)
        except Exception as exc:
            _fail(exc)

    if service.allow_control:
        @mcp.tool(
            name="start_irrigation",
            description=(
                "启动水泵。必须传入 confirm=\"%s\"。运行时长由设备 max_run_s 强制限制，"
                "MCP 不能覆盖该限制；启动后应调用 stop_irrigation 停止。" % CONFIRM_START
            ),
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
        )
        def start_irrigation(confirm: str, request_id: str | None = None) -> dict[str, Any]:
            try:
                return service.start_irrigation(confirm, request_id)
            except Exception as exc:
                _fail(exc)

        @mcp.tool(
            name="set_irrigation_mode",
            description="设置 auto/manual 模式。必须传入 confirm=\"%s\"。" % CONFIRM_MODE,
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
        )
        def set_irrigation_mode(mode: str, confirm: str) -> dict[str, Any]:
            try:
                return service.set_irrigation_mode(mode, confirm)
            except Exception as exc:
                _fail(exc)

        @mcp.tool(
            name="set_soil_threshold",
            description=f"设置土壤湿度阈值（0–100%）。必须传入 confirm=\"{CONFIRM_THRESHOLD}\"。",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
        )
        def set_soil_threshold(percent: float, confirm: str) -> dict[str, Any]:
            try:
                return service.set_soil_threshold(percent, confirm)
            except Exception as exc:
                _fail(exc)

        @mcp.tool(
            name="apply_plant_profile",
            description="应用植物档案和生长阶段。必须传入 confirm=\"%s\"。" % CONFIRM_PROFILE,
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
        )
        def apply_plant_profile(profile: str, stage: str, confirm: str) -> dict[str, Any]:
            try:
                return service.apply_plant_profile(profile, stage, confirm)
            except Exception as exc:
                _fail(exc)

        @mcp.tool(
            name="import_plant_profiles",
            description="导入植物档案 JSON。必须传入 confirm=\"%s\"。" % CONFIRM_IMPORT,
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
        )
        def import_plant_profiles(payload: dict[str, Any], confirm: str) -> dict[str, Any]:
            try:
                return service.import_plant_profiles(payload, confirm)
            except Exception as exc:
                _fail(exc)

    # --------------------------------------------------------------- resources
    @mcp.resource("agriverse://state", name="AgriVerse Device State", mime_type="application/json")
    def state_resource() -> str:
        return json.dumps(service.get_state(), ensure_ascii=False)

    @mcp.resource("agriverse://sensors", name="AgriVerse Sensors", mime_type="application/json")
    def sensors_resource() -> str:
        return json.dumps(service.get_sensors(), ensure_ascii=False)

    @mcp.resource("agriverse://config", name="AgriVerse Public Config", mime_type="application/json")
    def config_resource() -> str:
        return json.dumps(service.get_config(), ensure_ascii=False)

    @mcp.resource("agriverse://profiles", name="AgriVerse Plant Profiles", mime_type="application/json")
    def profiles_resource() -> str:
        return json.dumps(service.get_plant_profiles(), ensure_ascii=False)

    # ----------------------------------------------------------------- prompts
    @mcp.prompt(name="daily_briefing", description="生成当天环境、适宜度和灌溉状态简报")
    def daily_briefing() -> str:
        return (
            "请先调用 get_environment、get_suitability、get_irrigation_status 和 get_sensor_status，"
            "再用中文给出今天的环境简报。必须引用真实数值和时间；不要编造传感器读数。"
            "如果数据 stale 或 invalid，明确指出。"
        )

    @mcp.prompt(name="irrigation_advice", description="基于当前环境给出灌溉建议")
    def irrigation_advice() -> str:
        return (
            "请先读取 get_environment、get_suitability、get_irrigation_status 和 get_history('12h')。"
            "结合当前植物档案给出是否灌溉、建议原因和风险；不要直接启泵，除非用户明确要求并确认。"
            "如果用户要求启泵，必须先说明设备 max_run_s，再调用 start_irrigation 并传入确认串。"
        )

    @mcp.prompt(name="anomaly_triage", description="排查传感器或灌溉异常")
    def anomaly_triage() -> str:
        return (
            "请调用 diagnose、get_sensor_status 和 get_irrigation_status。"
            "按“传感器、网络、灌溉、数据新鲜度”分类列出问题，不要猜测未返回的数据。"
        )

    return mcp
