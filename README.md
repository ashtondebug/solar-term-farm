# AgriVerse（节气智农）

AgriVerse 是一个以 **ESP32-S3 N16R8 + MicroPython** 为核心的智能农业物联网项目：采集土壤湿度、空气温湿度与光照，计算植物环境适宜度，执行受安全约束的自动/手动灌溉，并通过局域网 Web 页面与淘晶驰 TJC 串口屏进行本地交互。

项目仓库为**私人仓库**，当前处于 M1 垂直切片阶段。

## 当前状态（M1）

已经完成：

- ESP32-S3 固件骨架：配置、状态、时间、日志、存储、传感器、适宜度、节气、灌溉安全状态机、HTTP API。
- 主机模拟器：用真实 API/控制器/状态代码驱动浏览器页面，数据明确标注为模拟值。
- Web 管理页：保留原有视觉基准，六个页面接入 `/api/v1/*`，支持离线提示、设备状态、灌溉控制、参数保存、PIN 输入与二十四节气切换。
- Wi-Fi 自动重连与配网状态机：扫描、连接、验证成功后才保存、连续 5 次失败转配网；屏幕 UI 待接。
- 主机测试：`57` 项全部通过；HTTP 服务、API、灌溉状态机、土壤校准、SHT31、节气算法、时间纪元、Wi-Fi 配网状态机均有覆盖。
- 部署脚本：`tools/install.bat`、`tools/start.bat`、`tools/deploy.py`、`tools/build_web.py`。
- 文档：架构、硬件、GPIO、API、部署、测试、串口屏资料阅读记录。

尚未完成 / 未验证：

- 真实硬件读数、继电器电气行为、RGB LED 引脚、屏幕电平与串口屏工程。
- 触摸屏 `.HMI` 工程（USART HMI 闭源格式，需在上位机中搭建）。
- Wi-Fi 屏幕配网页面、完整 24 节气长文案、MCP Server。
- 设备端 PIN 默认关闭（`security.require_pin=false`），M1 仅保留 API 与 UI 的 401 流程。

## 硬件

| 部件 | 型号 / 说明 |
|---|---|
| 主控 | ESP32-S3 N16R8（16 MB Flash / 8 MB PSRAM） |
| 触摸屏 | 淘晶驰 TJC3224T128_011R_A01，2.8 英寸，320×240，电阻触摸，UART |
| 土壤湿度 | HW-390 V2.0 电容式，VCC/GND/AOUT，AOUT 接 GPIO4（ADC） |
| 空气温湿度 | SHT31，I²C，SDA=GPIO8，SCL=GPIO9 |
| 光照 | BH1750，I²C，与 SHT31 共用总线 |
| 灌溉执行 | 3.3V 供电、**高电平触发**继电器，IN=GPIO5；低压直流水泵 |
| 水位检测 | **不安装**，系统不提供水位/缺水自动检测 |

### 继电器安全逻辑（强制）

- GPIO5 输出 **3.3V HIGH**：继电器吸合，水泵运行。
- GPIO5 输出 **0V LOW**：继电器释放，水泵停止。
- 上电、复位、GPIO 高阻期间必须保持 LOW；继电器 IN 需要硬件下拉，水泵回路使用 COM/NO 常开触点。
- 软件初始化与超时保护只是第二道保险，不能替代硬件下拉与常开触点。
- 所有客户端只能提交启动/停止意图，GPIO 只能由 `ESP/irrigation/relay.py` 持有。

## 快速开始（无需硬件）

在 Windows 10/11 的普通用户下：

```bat
tools\start.bat
```

或直接使用系统 Python（模拟器只依赖标准库）：

```bat
python tools\build_web.py
python tools\devserver.py --port 8080 --open
```

浏览器打开 `http://127.0.0.1:8080/`。页面顶部会显示「开发模拟器」，所有数值来自模拟后端，不是真实设备。

`tools\install.bat` 只用于安装 `mpremote` / `esptool` 等部署工具，不运行模拟器也可以不安装。

## 运行测试

```bat
python -m unittest discover -s tests -v
```

预期：

```text
Ran 57 tests in ...
OK
```

也可使用：

```bat
python tools\run_tests.py
```

## 目录结构

```text
AgriVerse/
├─ agriverse_admin_dashboard.html   # 唯一 UI 视觉源文件
├─ app.js                           # 前端数据层（API、渲染、PIN、离线）
├─ app.css                          # M1 新增状态/表单/弹窗样式
├─ ESP/                             # MicroPython 固件
│  ├─ main.py                       # 组合根与异步任务
│  ├─ config.py                     # 配置默认值与校验
│  ├─ core/                         # 状态、日志、时间、校验
│  ├─ sensors/                      # 土壤 / SHT31 / BH1750
│  ├─ suitability/                  # 适宜度模型与植物配置
│  ├─ solar_terms/                  # 24 节气数据 + 太阳黄经
│  ├─ irrigation/                   # 继电器、状态机、历史
│  ├─ storage/                      # 原子 JSON / 历史 JSONL
│  ├─ network/                      # Wi-Fi 状态机
│  └─ web/                          # HTTP API / 静态服务
├─ Touch_screen/                    # 串口屏页面规格与资源说明
├─ docs/                            # 架构、硬件、API、测试、TJC 资料
├─ tools/                           # 构建、模拟器、部署、测试
├─ tests/                           # 标准库 unittest
├─ README.md
└─ PROGRESS.md
```

`ESP/web/static/` 为构建产物，由 `tools/build_web.py` 从根目录 UI 源文件生成，不手工编辑。

## 局域网 Web API

基础路径 `/api/v1`，同一局域网内由 ESP32-S3 提供：

- `GET /state`：传感器、适宜度、节气、灌溉、网络、配置快照。
- `GET /history?range=12h|24h|7d`：历史点。
- `GET /solar-terms`：24 节气元数据。
- `GET /config` / `PUT /config`：公开配置与参数保存。
- `POST /irrigation/commands`：`{"action":"start|stop","request_id":"..."}`。
- `POST /time`：浏览器校时 `{"epoch":...}`。
- `GET /health`：轻量探活。

详见 [docs/API.md](docs/API.md)。

## 烧录与部署

1. 安装 MicroPython 固件到 ESP32-S3（需按开发板确认固件与 USB 模式）。
2. 运行 `tools\install.bat` 安装 `mpremote` / `esptool`。
3. 连接开发板，执行：

```bat
python tools\deploy.py --port COM6
```

部署脚本会把 `ESP/` 下的 `.py` 与构建后的 Web 静态文件写入板端；`/data/wifi.json` 需要按你的网络填写（格式见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)）。

## 已知限制

- 真机未接入时，所有传感器/灌溉结论只代表主机仿真，不代表硬件已验证。
- 串口屏工程尚未创建；TJC 命令/变量协议只记录了已核实的页面与返回格式。
- 18 个节气的长文案尚未补齐，UI 会显示「暂无收录」而不是编造内容。
- 设备 PIN 默认关闭；启用前需要先完成屏幕或设置页的 PIN 展示流程。
- 本项目不使用云服务器，不依赖互联网；MCP 扩展尚未实现，但 API 已为后续 MCP Server 提供稳定接口。

## 安全与隐私

- 仓库为私人仓库；不包含 Wi-Fi 密码、设备 PIN 或云服务密钥。
- Wi-Fi 凭证只保存在设备 `/data/wifi.json`，不上传、不在 API 返回、不写入日志。
- 管理页面不展示已保存的 Wi-Fi 密码。
- 继电器默认关闭不能依赖软件；请先完成硬件下拉与 COM/NO 接线核对。
