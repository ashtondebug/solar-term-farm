# 架构说明（M1）

## 1. 目标

设备在**无云、无互联网**的局域网中独立运行：采集环境数据、计算适宜度、执行受约束的灌溉、向浏览器、TFT 和 MCP 提供一致状态。Web、TFT、按钮与 MCP 都只是客户端/意图源，不拥有硬件。

## 2. 分层

```text
浏览器 / TFT / MCP Server / GPIO41 按钮
        │ HTTP / I²C / HTTP / intent
        ▼
ESP/web/api.py  ── 统一 JSON envelope、鉴权、参数校验
        │
        ▼
DeviceState（唯一状态源） ◄── SensorManager / IrrigationController
        │
        ├── irrigation/controller.py（唯一能操作 Relay 的状态机）
        ├── suitability/model.py（区间 + 权重 + 惩罚）
        └── solar_terms/astronomy.py（太阳黄经）
        │
        ▼
Relay(GPIO5) / I²C / ADC / Wi-Fi
```

硬件访问只出现在 `ESP/main.py` 组合根。驱动通过构造函数接收 `i2c` / `adc` / `pin`，因此同一套逻辑可由 CPython 测试与模拟器复用。

## 3. 数据流

1. `sensor_loop` 每 `sampling.interval_s`（默认 30 秒）轮询传感器。
2. `SensorManager` 将读数写入 `DeviceState`；失败/未校准标记为无效，不伪造数值。
3. `suitability.evaluate()` 读取本次读数；任一数据无效或过期返回 `score=None`。
4. 每 `sampling.history_interval_s`（默认 300 秒）写入一个历史点。
5. `control_loop` 每 1 秒调用 `IrrigationController.tick()`；所有自动/手动启动都经过同一个 `can_start()`。
6. `WebServer` 读取 `DeviceState` 快照并序列化；控制请求调用控制器，不直接写 GPIO。
7. `network_loop` 维护 Wi-Fi 状态；离线不影响采集、显示和自动灌溉。

## 4. 状态与安全不变量

- `DeviceState` 是唯一事实源；API 返回的 `data` 就是它的快照（加上公开配置与节气缓存）。
- `Relay` 是唯一持有 GPIO5 的类；初始化即写 LOW；任何其他模块不得直接调用 `Pin.value`。
- `IrrigationController` 是唯一能启动/停止水泵的对象；`can_start()` 检查故障、已运行、最小停泵时间。
- 最长运行时间由 `tick()` 强制执行；超时、异常、重启、GPIO 故障都落到 LOW。
- 传感器无效/过期时禁止自动灌溉；手动仍受最长运行与故障锁存限制。
- 软件默认关闭不是安全保证；硬件 IN 下拉 + COM/NO 是主保护。

## 5. 传输选择

- **HTTP 轮询 2 秒**，`document.hidden` 时暂停；失败指数退避到 30 秒。
- 统一 envelope：`{"ok":true,"data":...,"ts":...}` / `{"ok":false,"error":{...}}`。
- 控制请求带 `request_id`，控制器 60 秒内幂等。
- 不使用 WebSocket：当前端点少、数据量小，轮询的断线行为更容易验证；后续需要时加 SSE。

## 6. 存储

- `/data/config.json`：设备名、采样、灌溉、植物、校准、GPIO、特性开关、PIN。
- `/data/wifi.json`：SSID / 密码，单独文件；由 `netmgr/store.py` 原子写，不通过 API 返回。
- Wi-Fi 配网：`netmgr/manager.py` 负责扫描、连接、验证；只有新网络验证成功后才替换旧配置，连续 5 次失败转 `provisioning`；密码不进公开状态。
- `/data/history/history.jsonl`：5 分钟一点，7 天保留，256KB 轮转。
- 配置采用 tmp + rename 原子写；损坏时备份 `.bak` 并使用默认配置。
- 断电最多丢 5 分钟历史；历史写入频率约 288 次/天，远低于 Flash 寿命压力。

## 7. 内存与性能

- 历史点只保留 7 天（约 2016 点），内存按需裁剪。
- 静态页面按 1KB 分块发送，不整体读入 RAM。
- 节气计算每小时缓存一次；太阳黄经为低精度 Meeus 级数，CPU 开销小。
- 单请求 body 上限 4KB、header 上限 8KB、请求超时 5 秒。

## 8. M1 范围与后续

M1 已实现：配置/状态/存储、三传感器、适宜度、24 节气算法与元数据、灌溉状态机、HTTP API、Web 数据层、模拟器、测试与文档。

后续：真机 bring-up、Wi-Fi 配网验证、TFT/按钮实测、二十四节气长文案、MCP 工具验收。详见 `PROGRESS.md`。
