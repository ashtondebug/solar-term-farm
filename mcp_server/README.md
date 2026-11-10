# AgriVerse MCP Server

Windows PC 上的 MCP bridge：把 AgriVerse ESP32-S3 的 REST API 暴露为 MCP 工具、资源和提示词。

ESP32 **不运行 MCP Server**，它仍然是设备端安全控制的唯一所有者。

## 前提

- Windows 10/11，Python 3.11+；
- 电脑与 ESP32 在同一局域网；
- 设备 API 可访问，例如 `http://192.168.153.234/api/v1/health` 返回 200；
- 水泵控制需要 `AGRI_ALLOW_CONTROL=1`。

## 安装

```powershell
cd D:\Dev\ESP32S3\AgriVerse\mcp_server
.\install.ps1
```

脚本会创建带 `--system-site-packages` 的 `.venv`，复用本机已有的 setuptools/MCP 依赖，并以 `--no-build-isolation` 安装本包，避免镜像缺少构建依赖时失败。

## DSH 内置 MCP client

DSH 自带官方 `@deepseek-ai/dsh-mcp-client`，不需要 Claude Code。本机已安装到 desktop profile：

```powershell
dsh plugin --profile desktop add @deepseek-ai/dsh-mcp-client@0.2.2-rc.1
```

已把 AgriVerse 写入：

```text
C:\Users\kjld2\.dsh\profiles\desktop\cordis.patch.yml
```

条目（注意：新条目必须放在 `insert:` 下）：

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
        failOnStartupError: false
```

**这个条目只在 DSH 宿主启动时加载。** 修改后需要完全退出 DeepSeek Harness（包括托盘进程），再重新打开；Web 页面刷新不会加载它。

重启后模型工具名形如：

```text
mcp__agriverse__get_environment
mcp__agriverse__get_irrigation_status
mcp__agriverse__start_irrigation
mcp__agriverse__stop_irrigation
```

## 其他 MCP 客户端

复制 `mcp.example.json` 中对应条目到客户端配置。Claude Desktop 的配置位于：

```text
%APPDATA%\Claude\claude_desktop_config.json
```

把 `command`/`cwd` 改成你电脑上的实际路径。

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `AGRI_BASE_URL` | `http://192.168.153.234` | ESP32 地址 |
| `AGRI_PIN` | 空 | 设备启用 PIN 时填写；只放客户端 env，不放仓库 |
| `AGRI_ALLOW_CONTROL` | `0` | `1` 才注册启泵/阈值/模式/档案工具 |
| `AGRI_TIMEOUT_S` | `8` | HTTP 超时 |
| `AGRI_MCP_TRANSPORT` | `stdio` | `stdio` 或 `streamable-http` |
| `AGRI_MCP_HOST` | `127.0.0.1` | HTTP 绑定地址 |
| `AGRI_MCP_PORT` | `8765` | HTTP 端口 |

## 启动

stdio（推荐，由 MCP 客户端拉起）：

```powershell
$env:AGRI_BASE_URL = "http://192.168.153.234"
$env:AGRI_ALLOW_CONTROL = "1"
.\.venv\Scripts\python.exe -m agriverse_mcp
```

HTTP（只绑定本机，除非你明确需要局域网访问）：

```powershell
.\.venv\Scripts\python.exe -m agriverse_mcp --transport streamable-http --host 127.0.0.1 --port 8765
```

stdio 模式不监听端口，不需要 Windows 防火墙入站规则。

## 工具

### 只读

- `get_environment`：空气温度、空气湿度、土壤湿度、光照；带 `age_s`/`stale`；
- `get_sensors`：全部传感器明细；
- `get_sensor_status`：有效性汇总；
- `get_suitability`：适宜度、档案、阶段；
- `get_solar_term`：当前节气；
- `get_irrigation_status`：水泵、模式、剩余时间、阈值、故障；
- `get_history`：`12h` / `24h` / `7d`；
- `get_irrigation_history`：最近灌溉动作；
- `get_plant_profiles`：档案和阶段；
- `get_config`：公开配置，PIN/密码/Token 脱敏；
- `get_health`：版本、运行时间；
- `diagnose`：传感器过期、网络、灌溉故障汇总。

### 控制

`stop_irrigation` 始终可用。

只有 `AGRI_ALLOW_CONTROL=1` 时才注册：

- `start_irrigation(confirm="START_IRRIGATION")`
- `set_irrigation_mode(mode, confirm="SET_MODE")`
- `set_soil_threshold(percent, confirm="SET_THRESHOLD")`
- `apply_plant_profile(profile, stage, confirm="APPLY_PROFILE")`
- `import_plant_profiles(payload, confirm="IMPORT_PROFILES")`

`start_irrigation` **不接受任意运行时长**。实际运行时间由设备 `max_run_s` 控制（默认 20 秒），MCP 不能绕过。停止由设备 `stop_irrigation` 处理。

## 安全边界

- 不直接写 GPIO；所有控制走 `/api/v1/irrigation/commands`；
- 设备端 `IrrigationController` 仍负责 `max_run_s`、`min_off_s`、故障锁存；
- 默认只读；控制工具必须显式开启；
- `stop_irrigation` 不受只读开关影响；
- PIN 不写入日志、不返回给客户端；
- WiFi 密码和 Token 不返回；
- `start_irrigation` 需要精确确认串；
- 每次控制写 `agriverse.mcp.audit` 日志到 stderr（工具名、request_id，不含 PIN）；
- MCP 不可用时，设备本地自动灌溉和网页仍正常运行。

## 测试

无需设备：

```powershell
cd D:\Dev\ESP32S3\AgriVerse
python -m unittest discover -s mcp_server/tests -t mcp_server -v
```

真实设备冒烟（只读 + stop，不启泵）：

```powershell
$env:AGRI_BASE_URL = "http://192.168.153.234"
$env:AGRI_ALLOW_CONTROL = "1"
python mcp_server/tests/smoke_device.py
```

项目现有固件/网页测试：

```powershell
python -m unittest discover -s tests
```

## 已知限制

- 当前只支持 Windows PC 作为 MCP host；电脑休眠时 MCP 不可用；
- 设备 API 是局域网 HTTP，没有 TLS；不要把端口暴露到公网；
- PIN 目前通过环境变量传入；后续可接 Windows Credential Manager；
- 没有 MCP 控制限速器；设备端最小停泵、最大运行时间仍是最终保护；
- `start_irrigation` 无法指定时长，因为设备 API 不支持按请求覆盖 `max_run_s`。

## 相关文档

- `../docs/MCP.md`
- `../docs/API.md`
- `../AGENT.md` 第 11 节
