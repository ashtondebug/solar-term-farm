# AgriVerse 开发进度

> 本文件是跨会话续作入口。每次完成功能、修复或优化后追加记录，并同步「当前状态 / 待办 / 已知问题」。
>
> 最后更新：2026-11-07（M1 垂直切片）

## 当前状态

| 项 | 状态 |
|---|---|
| 阶段 | M1：主机可运行垂直切片 |
| 固件骨架 | 完成（未真机验证） |
| 传感器/适宜度/节气/灌溉 | 代码与单测完成，真机未验证 |
| Web API | 完成，模拟器与 CPython 集成测试通过 |
| Web 页面 | 六页接入 API，视觉基准保留 |
| 串口屏 | 仅资料记录与页面规格，无 `.HMI` |
| MCP | 未实现，接口已预留 |
| 真机 | 未接入 |
| Git | 有未提交改动；提交/推送需用户确认 |

## 本次会话完成（2026-11-07）

### 1. 仓库与基线

- 私有仓库 `ashtondebug/AgriVerse` 已创建，基线提交 `0a6f20d`，作者/提交者 `AshtonDebug <debug_life@qq.com>`。
- 基线内容：`AGENT.md`、`agriverse_admin_dashboard.html`、`.vscode/settings.json`。
- 推送时本机全局 Git 代理 `127.0.0.1:7890` 不可用，使用空代理 + OpenSSL 后端 + `gh` 凭据完成。

### 2. M0 工程骨架

- `ESP/config.py`：默认配置、深度合并、范围/校准/PIN/GPIO 唯一性校验。
- `ESP/core/`：`DeviceState` 单一状态源、日志、`SystemClock`、校验工具。
- `ESP/storage/`：原子 JSON 配置、JSONL 历史、容量/保留策略。
- `ESP/network/manager.py`：非阻塞 Wi-Fi 重连状态机（配网流程待做）。
- `ESP/main.py`：安全优先的组合根；GPIO5 先拉低，再加载配置/服务/任务。
- `tools/`：`build_web.py`、`devserver.py`、`deploy.py`、`run_tests.py`、`install.bat`、`start.bat`。

### 3. 传感器与算法

- `sensors/soil.py`：HW-390 两点校准，支持端点顺序反转、量程校验、未校准标记。
- `sensors/sht31.py`：单次高重复性读取、CRC8、错误成对返回。
- `sensors/bh1750.py`：连续高分辨率模式。
- `sensors/manager.py`：轮询、异常隔离、失败计数、`air_temp`/`air_humidity` 拆分。
- `suitability/`：区间得分 + 权重 + 严重异常封顶；数据无效/过期返回 `None`，不出假分数。
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

### 6. 验证记录

```text
python -m compileall -q ESP tools tests    -> exit 0
python -m unittest discover -s tests -v    -> Ran 50 tests ... OK
```

API 冒烟（模拟器 `127.0.0.1:8099`）：

```text
state.ok=True, source=simulator, time_synced=True
soil=43.819%, air_temp=22.9C, air_humidity=59.914%, light=7753.436lx
suitability=100/good, solar_term=立冬/225, history.points=143, terms=24
GET / = 200 (31875 bytes), GET /app.js = 200 (45632 bytes)
start -> ok, pump=True, remaining=20; stop -> ok, pump=False
PUT config threshold=45 -> ok; invalid max_run=999 -> 422
```

截图：`artifacts/m1-overview.png` 等（本地产物，未入库）。

## 已知问题 / 未验证

1. **真机完全未验证**：传感器读数、I²C 地址/上拉、ADC 校准、继电器吸合、泵电流、RGB LED 均未实测。
2. **PIN 默认关闭**：`security.require_pin=false`；API/UI 的 401 流程已实现，等屏幕能展示 PIN 后启用。
3. **串口屏工程缺失**：仅完成资料阅读与页面规格；`.HMI` 需 USART HMI 上位机创建。
4. **18 个节气长文案缺失**：UI 明确显示「暂无收录」，不伪造。
5. **Wi-Fi 配网未实现**：仅支持 `/data/wifi.json` 预置 + 5 次失败状态；屏幕配网待 M3。
6. **MCP 未实现**：`docs/` 与 API 已为 MCP Server 预留稳定接口。
7. **`deploy.py` 未在板端执行**：`mpremote` 未安装；脚本为待验证状态。
8. **主目录 UI 与构建产物**：`ESP/web/static/*` 由 `tools/build_web.py` 生成，`.gitignore` 忽略；根目录 HTML 是唯一视觉源。
9. **截图依赖 Edge headless**：`artifacts/` 不入库，仅用于本地验收。

## 下一步（按优先级）

- [ ] **M2 真机 bring-up**：核对开发板原理图、RGB LED、GPIO5 下拉、继电器/泵额定；接入 SHT31/BH1750/HW-390；记录实测值。
- [ ] **M2 安全实测**：上电/复位/拔 USB/程序卡死四种场景泵必须停；最长运行、故障锁存、看门狗。
- [ ] **M3 配网与配置**：TJC 扫描/SSID/密码/连接状态；`/data/wifi.json` 原子保存；连续 5 次失败转配网；PIN 展示与启用。
- [ ] **M4 内容**：补齐 18 个节气长文案；植物档案与阶段；适宜度权重可配置。
- [ ] **M5 屏幕**：在 USART HMI 创建 5 页工程，按 `Touch_screen/docs/` 变量表对接 UART 协议。
- [ ] **M6 MCP**：PC 端 stdio MCP Server，10 个工具，复用现有 REST + PIN；不成为核心依赖。
- [ ] 提交前：跑 50 项测试 + 模拟器冒烟 + 更新本文件 + 汇总改动，等待用户确认后**一次**提交/推送。

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
