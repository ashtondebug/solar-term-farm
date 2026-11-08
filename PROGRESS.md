# AgriVerse 开发进度

> 本文件是跨会话续作入口。每次完成功能、修复或优化后追加记录，并同步「当前状态 / 待办 / 已知问题」。
>
> 最后更新：2026-11-08（M2 A1–A4；M4 节气内容；M4B 植物档案/阶段/权重/JSON 导入/traits 展示；环境趋势四序列；内存拆分）

## 当前状态

| 项 | 状态 |
|---|---|
| 阶段 | M1 垂直切片 + M3A 配网状态机 |
| 固件骨架 | 完成（未真机验证） |
| 传感器/适宜度/节气/灌溉 | 代码与单测完成，真机未验证 |
| Web API | 完成，模拟器与 CPython 集成测试通过 |
| Web 页面 | 六页接入 API，视觉基准保留 |
| Wi-Fi 配网 | 设备端状态机完成（M3A）；屏幕 UI 待接 |
| 串口屏 | 仅资料记录与页面规格，无 `.HMI` |
| MCP | 未实现，接口已预留 |
| 真机 | 未接入 |
| Git | M1 已推送 `14a2478`；M3A 随本次会话提交 |

## 本次会话完成（2026-11-07）

### 1. 仓库与基线

- 私有仓库 `ashtondebug/AgriVerse` 已创建，基线提交 `0a6f20d`，作者/提交者 `AshtonDebug <debug_life@qq.com>`。
- 基线内容：`AGENT.md`、`agriverse_admin_dashboard.html`、`.vscode/settings.json`。
- 推送时本机全局 Git 代理 `127.0.0.1:7890` 不可用，使用空代理 + OpenSSL 后端 + `gh` 凭据完成。

### 2. M0 工程骨架

- `ESP/config.py`：默认配置、深度合并、范围/校准/PIN/GPIO 唯一性校验。
- `ESP/core/`：`DeviceState` 单一状态源、日志、`SystemClock`、校验工具。
- `ESP/storage/`：原子 JSON 配置、JSONL 历史、容量/保留策略。
- `ESP/netmgr/`：非阻塞 Wi-Fi 自动重连 + M3A 配网状态机（扫描/连接/验证/5 次失败转配网）。
- `ESP/main.py`：安全优先的组合根；GPIO5 先拉低，再加载配置/服务/任务。
- `tools/`：`build_web.py`、`devserver.py`、`deploy.py`、`run_tests.py`、`install.bat`、`start.bat`。

### 3. 传感器与算法

- `sensors/soil.py`：HW-390 两点校准，支持端点顺序反转、量程校验、未校准标记。
- `sensors/sht31.py`：单次高重复性读取、CRC8、错误成对返回。
- `sensors/bh1750.py`：连续高分辨率模式。
- `sensors/manager.py`：轮询、异常隔离、失败计数、`air_temp`/`air_humidity` 拆分。
- `suitability/`：区间得分 + 档案/阶段权重 + 严重异常封顶；数据无效/过期返回 `None`，不出假分数。
- `solar_terms/`：24 节气元数据 + Meeus 低精度太阳视黄经边界；2024 立春/春分/冬至测试通过。

### 4. 灌溉安全

- `irrigation/relay.py`：唯一持有 GPIO5；3.3V 高电平触发；初始化即 LOW；故障锁存。
- `irrigation/controller.py`：自动/手动状态机、最长运行、最小停泵、自动间隔、传感器新鲜度、`request_id` 60 秒幂等。
- `irrigation/history.py`：最近 50 条记录，进行中记录单独展示。
- 单测覆盖：极性、最长运行、MIN_OFF、自动触发、过期数据、幂等、故障拒绝。

### 5. API 与 Web

- `web/api.py`：`/state`、`/history`、`/solar-terms`、`/config`、`/irrigation/commands`、`/time`、`/health`；统一 envelope、错误码、PIN 401、配置 422。
- `web/server.py`：MicroPython/CPython 兼容的最小 HTTP/1.1 服务；请求大小限制、超时、静态分块、路径穿越防护；CPython 集成测试通过。
- 前端：`app.js` 轮询 2 秒、指数退避、离线横幅、模拟器横幅、PIN 弹窗、设置表单、图表、节气切换、深链接 `#view`。
- UI 修正：
  - 第 96 行继电器文案改为 3.3V 高电平触发。
  - 设备页改为 `TJC3224T128_011R_A01 · 2.8 英寸`、`AgriVerse 0.1.0`。
  - 移除“演示数据”文案与写死参数；无数据时显示「—」。
- 无头浏览器逐页截图验证：overview / environment / irrigation / calendar / device / settings。

### 6. M3A Wi-Fi 配网状态机

- `netmgr/store.py`：`/data/wifi.json` 原子保存/读取/清除；密码不进入公开配置或日志。
- `netmgr/manager.py`：`unconfigured → idle → connecting → connected`，失败后 15 秒重试、最多 5 次，达到上限转 `provisioning`；连接超时 20 秒；错误码分类 `wrong_password` / `no_ap_found` / `connect_failed`。
- **真机发现**：`network` 与 MicroPython 内置模块重名，包已改名为 `netmgr`；主机测试没有覆盖这个导入冲突。
- 手动 `connect(ssid, password)`：验证成功后才替换旧配置；`cancel_provisioning()` 恢复旧网络；`forget()` 需显式调用。
- `main.py` 改为注入 `WifiStore` 并启动自动连接；网络任务仍由 supervised task 隔离。
- 新增 `tests/test_network.py`（7 项）：未配置、成功后保存、密码不出现在状态、5 次失败转配网、取消恢复、扫描去重排序、存储往返。
- 文档：`docs/WIFI_PROVISIONING.md`。

### 7. 验证记录

```text
python -m compileall -q ESP tools tests    -> exit 0
python -m unittest discover -s tests -v    -> Ran 64 tests ... OK
```

API 冒烟（模拟器 `127.0.0.1:8099`）：

```text
state.ok=True, source=simulator, time_synced=True
soil=43.819%, air_temp=22.9C, air_humidity=59.914%, light=7753.436lx
suitability=100/good, solar_term=立冬/225, history.points=143, terms=24
GET / = 200 (31803 bytes), GET /app.js = 200 (47931 bytes)
start -> ok, pump=True, remaining=20; stop -> ok, pump=False
PUT config threshold=45 -> ok; invalid max_run=999 -> 422
```

截图：`artifacts/m1-overview-final.png` 等（本地产物，未入库）。

## M2 真机 bring-up 记录（2026-11-08）

- 板子：ESP32-S3 N16R8，串口 `COM10`，USB `VID_303A&PID_4001`；MicroPython **1.29.0**（`ESP32_GENERIC_S3`）；板端仅有 `boot.py`，无旧 `main.py`。
- `GPIO5` 作为输入读取为 **0（低）**，继电器未吸合；泵未启动。
- I²C 扫描：BH1750 重新接线后为 `[0x23, 0x44]`；光照 **22.5 lx**（环境较暗），SHT31 **19.44 °C / 58.57 % RH**。
- 土壤 ADC 原始：`17844 / 17396 / 17748 / 17860 / 18004`（未标定）。
- 固件已用 `mpremote 1.29.0` 部署 **37 个文件**；硬复位后日志出现 `web server listening on 0.0.0.0:80`，无 `EADDRINUSE`、无任务崩溃。
- 真机发现并修复：`network` 包名与 MicroPython 内置 `network` 模块冲突，包已改名为 `netmgr`；旧板端 `network/` 已删除。
- 水泵 0.8 秒干转脉冲：GPIO5 `0 → 1 → 0`，复位后 `0`；用户确认继电器吸合、水泵实际转动。GPIO 控制链路与继电器/泵回路验证通过。
- 新增 `tools/provision_wifi.py`：本地 `getpass` 输入 SSID/密码，上传 `/data/wifi.json`，复位后读取串口 IP；密码不进入聊天或日志。
- Wi-Fi 已连接：设备 IP **192.168.0.100**；浏览器打开后完成校时，节气显示 **立冬**，Web 页面可正常加载。
- 真机 HTTP 修复：MicroPython 不支持 `latin-1`，HTTP 头改用 UTF-8；静态文件分块间补 `await writer.drain()`；清除 `server.py` 的 UTF-8 BOM。
- 前端修复：土壤未标定时图表仍绘制温度线，图例显示“土壤湿度未标定”；适宜度原因改为中文。
- 配置 API 已支持 `calibration`（`soil_dry`/`soil_wet`）；等待湿端原始值后写入。
- **总览改版**：底部“传感器状态”替换为“节气农事”卡：显示当前节气、季节/序号、本节气剩余天数、3 条农事建议和下一个节气；“查看全部”进入 24 节气页。1024px 下适宜度卡改回单列，修复重叠。
- **节气内容完整性**：24/24 节气均有 3 条农事 tips、3 条谚语、3 条习俗；全文放在 `culture.py`，设备端使用构建生成的 `solar-terms.json`，避免启动时把全文载入 RAM。
- **设备管理标定**：新增土壤干湿两点标定卡，可“读取当前 ADC”、保存/清除标定；`state.sensors.soil.raw` 已暴露到 API。标定保存后下一轮采样生效。
- **标定输入修复**：2 秒轮询不再覆盖未保存的输入；加入本地 `calibrationDraft`。CDP 实测：输入 `12345` 等 3 秒保留，读取当前填入 `50860` 后等 3 秒保留，湿端输入 `6789` 同样保留。
- **适宜度显示修正**：分项行改为“温度分/湿度分/土壤分/光照分”，并注明“分项得分（0–100），不是传感器读数”；100% 土壤对应土壤分 0、总分 45（过湿）。
- **图表更新逻辑**：图例不再仅凭历史点数显示“未标定”，改为按当前 `calibration` 显示“等待采样”；图表追加当前实时读数，土壤线/右轴能随当前值更新。
- **HTTP 异常兼容**：`HttpError` / `ApiError` 不再调用 MicroPython 缺失的 `Exception.__init__`，修复 404/校验异常时的 `connection failed`。
- **离线恢复**：Wi-Fi 显示 connected、RSSI −35，但 ARP/HTTP 全无响应；复位恢复。根因是浏览器并发连接耗尽 lwIP 套接字。Web 服务增加 `MAX_CLIENTS=6`、静态发送 10 秒超时、`wait_closed` 1 秒超时；30 个并发 API + 12 个混合静态/API 压测后 health=200、ping 正常。
- **M4 内存拆分**：`data.py` 核心元数据约 6.7 KB；谚语/习俗/农事全文放在仅构建时使用的 `culture.py`（约 28 KB）；`solar-terms.json`（约 31 KB）由构建生成并静态返回。设备空闲堆从约 40 KB 提升到约 83 KB，HTML 页面加载后仍保持 health=200。
- **环境趋势图**：温度左轴 °C、空气湿度/土壤湿度外右轴 %、光照内右轴 lx；四序列图例和轴标题已显示，并追加当前实时点。
- **M4B 植物特性展示**：导入档案支持 `traits`（株型、根系、根深、株高/株距、支撑、修剪、授粉、病害/虫害、光周期、耐寒/热害、水分策略、耐旱/涝、VPD/DLI、GDD、pH/EC/CO₂ 参考、来源/置信度）及阶段级 `days_to_next_stage`/`gdd_to_next_stage`/`advice`；节气“时令农事建议”下方和总览农事卡展示，实测 23 项。
- 截图：`artifacts/plant-traits-advice.png`（本地）。
- 截图：`artifacts/overview-score-fixed.png`（本地）。
- 截图：`artifacts/overview-solar.png`、`artifacts/overview-1024-fixed.png`、`artifacts/overview-farming.png`、`artifacts/device-calibration-data.png`（本地）。
- 说明：`/api/v1/health` 的 `uptime_s` 在传感器循环中每 30 秒更新，短时间读到 0 属正常采样粒度，不影响页面。
- 尚未测试：RGB LED、屏幕、程序卡死/看门狗、Wi-Fi 断网。
- 结论：SHT31、BH1750、土壤 ADC、GPIO5 默认关闭正常；固件已上板并能启动 Web 服务。

### A1–A4 真机验收结果（2026-11-08）

- **A1 基线**：`192.168.0.100`，RSSI −34～−38；uptime 996s；土壤 raw 17,300 / 96.1%；SHT31 19.13 °C / 58.99%；BH1750 4.17 lx；泵停止、auto/idle；历史 29 点；采样 30s / 历史 300s。
- **A2 标定**：干端 raw 50,764–50,780（稳定）；湿端（水）15,907–15,923（稳定）；差值 34,873；用户确认后覆盖为 **50,780 / 15,907**。正常土壤复验 raw 39,641 → **31.9%**，适宜度 **82 / good**。
- **A3 Web + soak**：Web `start` → `pump=true`，1 秒后 `stop` → `pump=false`；用户确认泵实际转动。300 次 `/state` 轮询 **300 成功 / 0 失败**，平均 317ms、最大 1,616ms，raw 16,307–17,540。
- **A4 安全**：复位后 `pump=false`/`idle`，标定保留；1 秒启停后立刻再启动返回 **409 MIN_OFF**；20 秒最长运行约 20 秒自动停；运行中拔 USB，泵**立即停止**、继电器释放，重新上电后 `pump=false`/`idle`，标定保留。
- **未测**：Wi-Fi 断网测试（用户要求跳过）；程序卡死/看门狗复位；RGB LED；串口屏。

## 已知问题 / 未验证

1. **真机已验收 A1–A4**：传感器、标定、Web 控制、10 分钟 soak、复位/最小间隔/20 秒最长运行/USB 拔电均已实测；Wi-Fi 断网、程序卡死/看门狗、RGB LED、屏幕仍未验证。
2. **PIN 默认关闭**：`security.require_pin=false`；API/UI 的 401 流程已实现，等屏幕能展示 PIN 后启用。
3. **串口屏工程缺失**：仅完成资料阅读与页面规格；`.HMI` 需 USART HMI 上位机创建。
4. **M4 内容完成**：24/24 节气 tips/谚语/习俗；植物档案/阶段/权重已实现；串口屏和 MCP 仍待完成。
5. **Wi-Fi 屏幕配网 UI 未接**：设备端状态机已完成（M3A），屏幕页面仍待 M5；当前可用 `/data/wifi.json` 预置。
6. **MCP 未实现**：`docs/` 与 API 已为 MCP Server 预留稳定接口。
7. **`deploy.py` 已在 COM10 上执行成功**（37 个文件）；`mpremote` 已安装；Wi-Fi 已连接 `192.168.0.100`，Web 可访问。
8. **`/api/v1/health` 的 `uptime_s` 每 30 秒采样更新**：短时间内读到 0 属正常；页面不依赖该字段。
9. **主目录 UI 与构建产物**：`ESP/web/static/*` 由 `tools/build_web.py` 生成，`.gitignore` 忽略；根目录 HTML 是唯一视觉源。
10. **截图依赖 Edge headless**：`artifacts/` 不入库，仅用于本地验收。

## 下一步（按优先级）

- [x] **M2 硬件识别**：COM10 / MicroPython 1.29.0 / SHT31 / BH1750 / GPIO5 默认低。
- [x] **M2 固件部署**：`deploy.py` 上传 37 个文件，硬复位后 Web 服务正常启动。
- [x] **M2 真机验收 A1–A4**：基线、两点标定、Web start/stop、300 次 soak、复位/最小间隔/20 秒最长运行/USB 运行中拔电。
- [ ] **M2 真机 bring-up**：核对开发板原理图、RGB LED、GPIO5 下拉、继电器/泵额定；接入 SHT31/BH1750/HW-390；记录实测值。
- [x] **M2 接线图初稿**：`docs/WIRING_DIAGRAM.svg`（待实物核对）。
- [ ] **M2 剩余安全项**：程序卡死/看门狗、Wi-Fi 断网（本次按要求跳过）；其余场景已通过。
- [x] **M3A 配网服务**：扫描/连接/验证/5 次失败转配网/密码不入状态；主机测试通过。
- [ ] **M3B 屏幕配网**：TJC 扫描/SSID/密码/连接状态；`/data/wifi.json` 原子保存；PIN 展示与启用。
- [x] **M4 节气内容**：24/24 节气各 3 条详细农事 tips、3 条谚语、3 条习俗；64 项测试通过。
- [x] **M4 植物档案/阶段/权重**：profile/stage、通用阶段倍率、四项自定义权重、设置页与评分结果展示；设备实测通过。
- [x] **M4B JSON 导入**：设置页文件导入、阶段级 ranges/weights、`/data/plants.json` 持久化、重启注册；JSON 校验与 64 项测试通过。
- [x] **M4B traits 展示**：株型/根系/根深/授粉/病害/水分策略/光周期/VPD/DLI 等特性在农事建议区展示；阶段 advice/积温/日温夜温参考；设备实测 23 项。
- [ ] **M5 屏幕**：在 USART HMI 创建 5 页工程，按 `Touch_screen/docs/` 变量表对接 UART 协议。
- [ ] **M6 MCP**：PC 端 stdio MCP Server，10 个工具，复用现有 REST + PIN；不成为核心依赖。
- [ ] 提交前：跑 64 项测试 + 模拟器冒烟 + 更新本文件 + 汇总改动，等待用户确认后**一次**提交/推送。

## 关键设计决策

| 决策 | 选择 | 理由 |
|---|---|---|
| 状态源 | 设备端 `DeviceState` 单一事实源 | Web/屏幕/MCP 不各自维护状态 |
| 通信 | HTTP 轮询 2s + 指数退避 | 简单、断线行为可预测；农业场景足够 |
| 固件并发 | asyncio 单线程 | 避免共享内存竞态；传感器读取毫秒级 |
| HTTP 服务 | 自研最小 HTTP/1.1 | 零第三方运行时依赖、可审计 |
| UI 源 | 根 HTML + `app.js/app.css`，构建复制到 ESP | 避免两份 UI 漂移 |
| 继电器 | 3.3V 高电平触发，GPIO5 | 按用户确认的硬件事实；软件绝不反转 |
| 土壤湿度 | 两点校准，未校准不出百分比 | 避免把 ADC 原始值伪装成含水率 |
| 适宜度 | 区间 + 权重 + 严重异常封顶 | 不允许严重异常被其他正常项抵消 |
| 节气 | 设备端太阳黄经计算 | Web/屏幕/MCP 共用；不按固定日期 |
| 测试 | 标准库 unittest + 注入 fake | 无 pytest 依赖；硬件边界清晰 |
