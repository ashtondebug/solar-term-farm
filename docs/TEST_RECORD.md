# 测试记录

日期：2026-11-07；真机验收：2026-11-08
环境：Windows 11（NT 10.0.26300），Python 3.13.14，Edge headless（截图）

## 1. 静态检查

```text
python -m compileall -q ESP tools tests
exit 0

node --check app.js
exit 0
```

## 2. 单元/集成测试

```text
python -m unittest discover -s tests -v
Ran 69 tests in 0.019s
OK
```

覆盖：配置、土壤校准、SHT31 CRC、适宜度、植物档案/阶段/权重、JSON 档案导入/校验、植物 traits/阶段建议展示、TFT 格式化、按钮灌溉意图、灌溉状态机、节气边界、24 节气农事/谚语/习俗、API、HTTP 解析、真实 HTTP socket 往返、历史存储、时间纪元、Wi-Fi 配网状态机。

## 3. 模拟器 API 冒烟

服务：`python tools/devserver.py --port 8099 --host 127.0.0.1`

```text
GET /api/v1/state
ok=True, source=simulator, time_synced=True
soil=43.819 %, air_temp=22.9 C, air_humidity=59.914 %, light=7753.436 lx
suitability=100/good, solar_term=立冬/225
history.points (12h) = 143, terms = 24

GET / = 200, 31803 bytes, contains app.js
GET /app.js = 200, 47931 bytes

POST /api/v1/irrigation/commands {"action":"start"}
ok, pump=True, state=manual, remaining=20
POST ... {"action":"stop"}
ok, pump=False

PUT /api/v1/config {"irrigation":{"soil_threshold":45}}
ok, threshold=45
PUT ... {"max_run_s":999}
HTTP 422, code=INVALID_CONFIG

GET /api/v1/history?range=bad
HTTP 400
GET /api/v1/history?range=7d
288 points
```

## 4. 页面验证

使用 Edge headless 逐页截图（`artifacts/`，未入库）：

- `m1-overview.png`
- `m1-environment.png`
- `m1-irrigation.png`
- `m1-calendar.png`
- `m1-device.png`
- `m1-settings.png`

检查点：

- 六页均显示 API 数据，不再出现硬编码 24.6/63/42/12,680。
- 顶部模拟器横幅可见；侧边栏连接状态为「在线 · 开发模拟器」。
- 灌溉页继电器文案为「3.3V 高电平触发：GPIO5 HIGH 启动，LOW 停止」。
- 设备页本地显示为 `2.8 英寸 ILI9341 TFT`（旧串口屏/OLED 设计已移除）。
- 节气页当前为立冬，太阳黄经 225°，24 节气下拉可选。
- 设置页参数为设备返回值，保存按钮存在。

## 5. 真机验收（2026-11-08）

设备：ESP32-S3 N16R8，COM10，MicroPython 1.29.0，IP `192.168.0.100`，Wi-Fi RSSI −34～−38 dBm。

### A1 只读基线

```text
device: model=ESP32-S3 N16R8, firmware=MicroPython, uptime=996s, time_synced=true
network: connected, ip=192.168.0.100, rssi=-34..-38
soil: raw=17300, value=96.1 %, valid=true
air: 19.13 C / 58.99 % RH; light=4.17 lx
irrigation: pump=false, mode=auto, state=idle
suitability: 45/poor (soil=13, temp=100, humidity=100, light=64)
history: 29 points (12h); sampling 30s, history 300s
```

### A2 土壤两点标定

```text
dry raw: 50764..50780 (stable, air/dry)
wet raw: 15907..15923 (stable, water)
span: 34873 (>= 500)
saved: soil_dry=50780, soil_wet=15907
normal soil check: raw=39641 -> 31.9 %, suitability 82/good
```

### A3 Web 控制与 10 分钟 soak

```text
POST start -> ok, pump=true, state=manual, remaining=20
1s later POST stop -> ok, pump=false, state=cooldown
user confirmed pump physically ran
soak: 300 requests, 300 ok, 0 failures
latency: avg 317 ms, max 1616 ms
raw range: 16307..17540
```

### A4 安全验收

```text
reset -> pump=false, idle, calibration persisted
start/stop then immediate start -> HTTP 409 MIN_OFF (min_off_s=5)
20s max run -> auto stop at ~20s, pump=false
USB unplug while pump running -> pump stopped immediately, relay released
replug -> pump=false, idle, uptime=30s, calibration persisted, IP restored
Wi-Fi disconnect -> not tested (user request)
```

## 6. 未验证

- TFT 常亮显示、GPIO41 按钮启停切换、5 秒排队与 20 秒自动停止。
- 设备 PIN 流程的真实交互（模拟器/PIN 默认关闭）。
- Wi-Fi 断网后的自动重连（本次按要求跳过）。
- 程序卡死/看门狗复位。
- RGB LED。
- 超过 10 分钟的长期运行、Flash 磨损。
- 植物档案/阶段/权重的更多作物样本与田间验证。

以上项在对应硬件/工程完成后补测，未测项不得写成「已通过」。
