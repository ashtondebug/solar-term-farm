# 部署与运行

## 1. 主机环境

- Windows 10 / 11，64 位，普通用户；不需要管理员权限，不修改注册表。
- Python 3.10+（当前验证：3.13.14）。
- 路径使用 `pathlib`，文件统一 UTF-8。
- Node.js 仅用于可选的 `node --check app.js` 语法检查，不是运行时依赖。

## 2. 主机模拟器（无硬件）

模拟器只依赖 Python 标准库：

```bat
python tools\build_web.py
python tools\devserver.py --port 8080 --open
```

或：

```bat
tools\start.bat
```

打开 `http://127.0.0.1:8080/`。页面顶部固定显示「开发模拟器」，API 响应带 `X-AgriVerse-Source: simulator`，不会把模拟值伪装成真实设备。

模拟器使用真实 `DeviceApi` / `IrrigationController` / `DeviceState`，只替换传感器、时钟和继电器引脚，因此能验证接口、状态机与页面契约。

## 3. 测试

```bat
python -m unittest discover -s tests -v
```

预期 `Ran 57 tests ... OK`。也可运行 `python tools\run_tests.py`。

## 4. 安装部署工具（可选）

```bat
tools\install.bat
```

会创建 `.venv` 并安装 `mpremote` / `esptool`。若网络不可用，可跳过；模拟器不需要这些依赖。

## 5. 烧录 MicroPython 固件

1. 从 MicroPython 官方下载适配 ESP32-S3 的固件（注意 Flash/PSRAM 配置）。
2. 确认开发板进入下载模式与 USB 串口。
3. 使用 `esptool` 擦除/写入固件（按开发板与固件说明操作）。
4. 用 `mpremote` 或串口 REPL 确认 `os.uname()`、`sys.implementation`。

> 固件版本、USB CDC 模式、Flash 分区以开发板实际为准；未验证前不要把 `tools/deploy.py` 当作已测试。

## 6. 部署项目文件

```bat
python tools\deploy.py --port COM6
```

脚本会：

- 先运行 `build_web.py` 生成 `ESP/web/static/index.html`、`app.js`、`app.css`。
- 在板端创建 `core/`、`sensors/`、`web/static/` 等目录。
- 逐个上传 `ESP/**/*.py` 与静态文件。
- 执行 `mpremote reset`。

先看清单而不写入：

```bat
python tools\deploy.py --dry-run
```

## 7. Wi-Fi 配置

设备端已实现扫描、连接、验证、5 次失败转配网（M3A，见 `docs/WIFI_PROVISIONING.md`）；屏幕配网页面尚未接入。当前可在板端 `/data/wifi.json` 预置：

```json
{"ssid": "YOUR_SSID", "password": "YOUR_PASSWORD"}
```

- 该文件不会通过 Web API 返回，也不写入日志。
- 连续 5 次连接失败后，`network.status` 变为 `provisioning`，等待后续屏幕配网流程。
- 没有 Wi-Fi 时，采集、适宜度、自动灌溉仍应运行；Web 无法访问。

## 8. 设备 PIN

M1 默认 `security.require_pin=false`，便于在屏幕尚未完成时调试。启用方式：

1. 等待 TJC 屏幕能显示设备 PIN，或在受控环境通过串口 REPL 读取配置；
2. 将 `/data/config.json` 的 `security.require_pin` 设为 `true`，`security.pin` 设为 6 位数字；
3. 重启后，控制/配置写入需要 `X-AgriVerse-Pin`；页面会弹窗要求输入。

不要把 PIN 写进 README、日志或 URL。

## 9. 常见问题

| 现象 | 处理 |
|---|---|
| `mpremote not found` | 运行 `tools\install.bat`，或 `python -m pip install mpremote` |
| 找不到串口 | 检查 USB 线/驱动；`GetPortNames()` 确认 COM 号；关闭占用串口的工具 |
| 页面打不开 | 确认设备已连 Wi-Fi 且 IP 可达；端口 80 未被占用 |
| 页面显示离线 | 设备未上电/未联网/HTTP 未启动；看串口日志 |
| 页面显示「开发模拟器」 | 当前连接的是主机 devserver，不是 ESP32 |
| 传感器显示「未标定」 | 先完成 HW-390 干湿两点校准，写入 `/data/config.json` |
| 水泵不启动 | 检查模式、阈值、最小停泵、故障锁存、继电器 IN 电平与硬件接线 |
| 控制返回 401 | `security.require_pin=true`，输入屏幕显示的 6 位 PIN |

## 10. 本机 Git 代理备注

本机曾出现全局 Git 代理 `127.0.0.1:7890` 不可用、Git 的 Schannel 报 `SEC_E_NO_CREDENTIALS` 的情况。仓库推送使用了一次性绕过（空代理 + OpenSSL 后端 + `gh` 凭据），未修改全局配置。若 VS Code 内 pull/push 失败，先检查该代理与 `http.sslBackend`。
