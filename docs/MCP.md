# AgriVerse MCP 接口

## 架构

```text
Claude Desktop / DSH
        │ MCP stdio（本地）或 Streamable HTTP（可选）
        ▼
Windows PC: agriverse-mcp
        │ HTTP REST
        ▼
ESP32-S3 AgriVerse /api/v1/*
```

ESP32 不运行 MCP Server。MCP bridge 只做协议适配、设备调用和安全包装；水泵仍由设备端 `IrrigationController` 控制。

## 传输

- 默认：stdio，由 MCP 客户端启动；
- 可选：Streamable HTTP，默认绑定 `127.0.0.1:8765`；
- 设备 API 是局域网 HTTP，没有 TLS；不要将 MCP HTTP 端口暴露到公网。

## DSH 宿主接入

DSH 自带 `@deepseek-ai/dsh-mcp-client`。本机已安装到 desktop profile：

```powershell
dsh plugin --profile desktop add @deepseek-ai/dsh-mcp-client@0.2.2-rc.1
```

配置位于：

```text
C:\Users\kjld2\.dsh\profiles\desktop\cordis.patch.yml
```

加入了 `mcp-agriverse` 条目，使用 stdio 启动。**新条目必须用 `insert:` 包裹**，否则 DSH 会把它当作不存在的已有 id 跳过：

```yaml
- insert:
    - id: mcp-agriverse
      name: "@deepseek-ai/dsh-mcp-client"
      config:
        serverName: agriverse
        transport: stdio
        command: 'D:\Dev\ESP32S3\AgriVerse\mcp_server\.venv\Scripts\python.exe'
        args: ['-m', 'agriverse_mcp']
        cwd: 'D:\Dev\ESP32S3\AgriVerse\mcp_server'
        env:
          AGRI_BASE_URL: 'http://192.168.153.234'
          AGRI_ALLOW_CONTROL: '1'
          AGRI_PIN: ''
          AGRI_TIMEOUT_S: '8'
        toolCallTimeoutMs: 20000
```

修改 `cordis.patch.yml` 后必须**完全退出并重新打开 DeepSeek Harness**，刷新网页不会重新加载宿主插件。重启后工具名：

```text
mcp__agriverse__get_environment
mcp__agriverse__get_irrigation_status
mcp__agriverse__start_irrigation
mcp__agriverse__stop_irrigation
```

不要使用 Claude Code 的 `claude mcp` 注册；DSH 是当前客户端。

## 工具

| 工具 | 类型 | 说明 |
|---|---|---|
| `get_environment` | 只读 | 四个环境传感器及 stale |
| `get_sensors` | 只读 | 全部传感器明细 |
| `get_sensor_status` | 只读 | 有效性汇总 |
| `get_suitability` | 只读 | 适宜度、档案、阶段 |
| `get_solar_term` | 只读 | 当前节气 |
| `get_irrigation_status` | 只读 | 泵、模式、剩余时间、故障 |
| `get_history` | 只读 | `12h` / `24h` / `7d` |
| `get_irrigation_history` | 只读 | 最近灌溉动作 |
| `get_plant_profiles` | 只读 | 档案和阶段 |
| `get_config` | 只读 | 公开配置，敏感字段脱敏 |
| `get_health` | 只读 | 版本、运行时间 |
| `diagnose` | 只读 | 传感器/网络/灌溉诊断 |
| `stop_irrigation` | 控制 | 始终可用，无需确认 |
| `start_irrigation` | 控制 | 需 `confirm="START_IRRIGATION"` |
| `set_irrigation_mode` | 控制 | 需 `confirm="SET_MODE"` |
| `set_soil_threshold` | 控制 | 需 `confirm="SET_THRESHOLD"` |
| `apply_plant_profile` | 控制 | 需 `confirm="APPLY_PROFILE"` |
| `import_plant_profiles` | 控制 | 需 `confirm="IMPORT_PROFILES"` |

控制工具只在 `AGRI_ALLOW_CONTROL=1` 时注册。`stop_irrigation` 例外，始终存在。

## 资源

- `agriverse://state`
- `agriverse://sensors`
- `agriverse://config`
- `agriverse://profiles`

## 提示词

- `daily_briefing`
- `irrigation_advice`
- `anomaly_triage`

## 安全

- 默认只读；
- 启泵需要精确确认串；
- 设备端 `max_run_s`、`min_off_s`、故障锁存始终生效；
- `start_irrigation` 不支持覆盖运行时长；
- PIN 只通过环境变量传入，不写日志；
- WiFi 密码、Token、PIN 不返回；
- 控制审计写入 `agriverse.mcp.audit` 日志；
- MCP 故障不影响设备本地自动灌溉和网页。

## 错误

错误以 MCP tool error 文本返回，保留设备错误码：

- `PIN_REQUIRED` / `PIN_INVALID`
- `ALREADY_RUNNING` / `MIN_OFF` / `FAULT`
- `DEVICE_TIMEOUT` / `DEVICE_UNREACHABLE`
- `CONTROL_DISABLED`
- `CONFIRM_REQUIRED`
- `BAD_RANGE` / `BAD_MODE` / `BAD_THRESHOLD`

## 测试

```powershell
python -m unittest discover -s mcp_server/tests -t mcp_server -v
python mcp_server/tests/smoke_device.py
```
