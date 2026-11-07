# MCP Server（预留，未实现）

AGENT.md 要求保留 MCP 扩展能力：ESP32-S3 不运行 MCP Server，未来在 PC 或局域网服务器上用 stdio 提供。当前 M1 **没有实现** MCP Server，只有稳定的设备 REST API。

## 计划

- 传输：stdio（标准 MCP），日志走 stderr，不使用 `print` 输出协议数据。
- 设备：通过 `http://<device-ip>/api/v1/*` 访问；控制类请求带 `X-AgriVerse-Pin`。
- 工具（按 AGENT.md 11.3）：
  - `get_environment`
  - `get_suitability`
  - `get_solar_term`
  - `get_irrigation_status`
  - `get_sensor_status`
  - `get_history`
  - `get_irrigation_history`
  - `set_irrigation_mode`
  - `start_irrigation`
  - `stop_irrigation`
- 每个工具需要完整 docstring：用途、何时调用、参数含义。
- 返回结构化、简短、有长度上限；错误返回明确 code/message。
- 外部 AI 只能提出建议或受控请求，最终执行权在设备端安全逻辑。
- MCP 不可用时，设备与局域网 Web 必须照常运行。

## 状态

待 M6 实现。API 契约见 `../docs/API.md`；不要在没有设备端校验的情况下让 MCP 直接操作 GPIO。
