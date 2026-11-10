# AgriVerse（节气智农）

AgriVerse 是一个以 **ESP32-S3 N16R8 + MicroPython** 为核心的智能农业物联网项目：采集土壤湿度、空气温湿度与光照，计算植物环境适宜度，执行受安全约束的自动/手动灌溉，并通过局域网 Web 页面和 2.8 英寸 SPI TFT 进行本地交互。

项目仓库为**私人仓库**，当前处于 M1 垂直切片阶段。

## 当前状态（M1）

已经完成：

- ESP32-S3 固件骨架：配置、状态、时间、日志、存储、传感器、适宜度、节气、灌溉安全状态机、HTTP API。
- 主机模拟器：用真实 API/控制器/状态代码驱动浏览器页面，数据明确标注为模拟值。
- Web 管理页：保留原有视觉基准，六个页面接入 `/api/v1/*`，支持离线提示、设备状态、灌溉控制、参数保存、PIN 输入、二十四节气切换、总览节气农事与土壤干湿两点标定；环境趋势图含温度、湿度、土壤与光照四条曲线；设置页可选植物档案、生长阶段与自定义权重，并可导入植物档案 JSON；农事建议区展示株型、根系、根深、授粉、病害、水分策略等 traits。
- Wi-Fi 自动重连与配网状态机：扫描、连接、验证成功后才保存、连续 5 次失败转配网；真机已连接，配网入口由 Web 页面提供。
- 主机测试：`69` 项全部通过；HTTP 服务、API、灌溉状态机、土壤校准、SHT31、节气算法、24 节气农事内容、植物档案/阶段/权重、JSON 档案导入、时间纪元、Wi-Fi 配网状态机、TFT 格式与按钮意图均有覆盖。
- 部署脚本：`tools/install.bat`、`tools/start.bat`、`tools/deploy.py`、`tools/build_web.py`。
- 文档：架构、硬件、GPIO、API、MCP、部署、测试。
- Windows MCP bridge：`mcp_server/`，18 个工具覆盖传感器、适宜度、节气、灌溉状态、历史、诊断、启停泵、模式、阈值和植物档案；已在 DSH 中以 `mcp__agriverse__*` 工具接入。

## 真机状态与未验证项

- 2.8 英寸 ILI9341 TFT 和 GPIO41 按钮尚未完成实物验证。
- 触摸屏设计已移除，不再维护 TJC/UART 屏幕工程。
- 长期泵运行与故障告警仍未验证。
- 设备端 PIN 默认关闭（`security.require_pin=false`），本版没有本地 PIN 显示入口。

## 硬件

| 部件 | 型号 / 说明 |
|---|---|
| 主控 | ESP32-S3 N16R8（16 MB Flash / 8 MB PSRAM） |
| TFT | 2.8 英寸 240×320 ILI9341，SPI，SCK=GPIO40，SDA=GPIO39，RST=GPIO38，DC=GPIO2，CS=GPIO1，3.3V，竖屏常亮 |
| 按钮 | GPIO41，高电平触发，内部下拉；按一次启动，再按一次停止 |
| 土壤湿度 | HW-390 V2.0 电容式，VCC/GND/AOUT，AOUT 接 GPIO4（ADC） |
| 空气温湿度 | SHT31，I²C，SDA=GPIO8，SCL=GPIO9 |
| 光照 | BH1750，I²C，与 SHT31 共用总线 |
| 灌溉执行 | 3.3V 供电、**高电平触发**继电器，IN=GPIO5；低压直流水泵 |
| 水位检测 | **不安装**，系统不提供水位/缺水自动检测 |

### 接线

完整引脚表见 [docs/GPIO_WIRING.md](docs/GPIO_WIRING.md)。TFT 使用 GPIO40/39 的 SPI，CS/DC/RST 为 GPIO1/2/38；SHT31/BH1750 保持在 GPIO8/9。按钮只提交灌溉意图，不直接操作继电器。

**本地交互：** TFT 竖屏常亮，每秒刷新空气温湿度、土壤、光照、水泵、适宜度和当前节气农事；GPIO41 高电平按钮按一次启动，再按一次停止；停泵后 5 秒内再按会自动排队，待 `min_off_s` 结束后启动；20 秒上限仍会自动停止。

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
Ran 68 tests in ...
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
│  ├─ netmgr/                       # Wi-Fi 状态机
│  └─ web/                          # HTTP API / 静态服务
├─ mcp_server/                      # Windows MCP bridge（stdio/HTTP）
├─ docs/                            # 架构、硬件、API、MCP、测试
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

## MCP（Windows PC）

MCP Server 运行在同一局域网的 Windows 电脑上，ESP32 仍是灌溉安全的最终执行者。DSH 已通过官方 `dsh-mcp-client` 接入，工具名为 `mcp__agriverse__*`：

```powershell
cd mcp_server
.\install.ps1
$env:AGRI_BASE_URL = "http://192.168.153.234"
$env:AGRI_ALLOW_CONTROL = "1"
.\.venv\Scripts\python.exe -m agriverse_mcp
```

- 默认只读；`AGRI_ALLOW_CONTROL=1` 才注册启泵、阈值、模式和档案工具；
- `start_irrigation` 必须传 `confirm="START_IRRIGATION"`，运行时长由设备 `max_run_s` 强制限制；
- `stop_irrigation` 始终可用；
- PIN 只从 `AGRI_PIN` 环境变量读取，不写入日志。

详见 [mcp_server/README.md](mcp_server/README.md) 与 [docs/MCP.md](docs/MCP.md)。

## 烧录与部署

1. 安装 MicroPython 固件到 ESP32-S3（需按开发板确认固件与 USB 模式）。
2. 运行 `tools\install.bat` 安装 `mpremote` / `esptool`。
3. 连接开发板，执行：

```bat
python tools\deploy.py --port COM6
```

部署脚本会把 `ESP/` 下的 `.py` 与构建后的 Web 静态文件写入板端。Wi-Fi 用本地脚本配置（密码不经过聊天）：

```bat
python tools\provision_wifi.py --port COM10
```

脚本会提示输入 SSID/密码，上传 `/data/wifi.json` 并复位，然后读取串口显示 IP 或失败原因。详见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。

## 已知限制

- 真机未接入时，所有传感器/灌溉结论只代表主机仿真，不代表硬件已验证。
- 串口屏设计已移除；TFT 常亮显示环境数据，按钮 GPIO41 按一次启动、再按一次停止。
- 24 个节气的农事、谚语和习俗均已补齐；植物档案/阶段、自定义权重已实现。
- 设备 PIN 默认关闭；本版没有本地 PIN 显示入口。
- 本项目不使用云服务器，不依赖互联网；MCP Server 运行在同一局域网的 Windows 电脑上，电脑休眠时 MCP 不可用，但不影响设备本地自动灌溉和网页。

## 安全与隐私

- 仓库为私人仓库；不包含真实 Wi-Fi 密码、设备 PIN 或云服务密钥。
- 本地开发凭据只放在被 `.gitignore` 忽略的 `ESP/wifi_secrets.py`；公开仓库只保留 `ESP/wifi_secrets.example.py` 的 `wifi_ssid` / `password` 占位符。
- 设备优先使用 `/data/wifi.json` 的已保存凭据；文件不存在时才回退到本地 `wifi_secrets.py`。
- Wi-Fi 密码不会通过 API 返回、不写入日志、不在管理页面展示。
- 提交前必须检查 `git status` 和 diff，禁止把 `ESP/wifi_secrets.py` 加入版本库。
- 继电器默认关闭不能依赖软件；请先完成硬件下拉与 COM/NO 接线核对。
