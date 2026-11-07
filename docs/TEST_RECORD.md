# 测试记录

日期：2026-11-07
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
Ran 57 tests in 0.019s
OK
```

覆盖：配置、土壤校准、SHT31 CRC、适宜度、灌溉状态机、节气边界、API、HTTP 解析、真实 HTTP socket 往返、历史存储、时间纪元、Wi-Fi 配网状态机。

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
- 设备页触摸屏为 `TJC3224T128_011R_A01 · 2.8 英寸`。
- 节气页当前为立冬，太阳黄经 225°，24 节气下拉可选。
- 设置页参数为设备返回值，保存按钮存在。

## 5. 未验证

- 真实 ESP32-S3 上的启动、传感器、I²C、ADC、继电器、水泵、Wi-Fi、看门狗。
- 串口屏 UART 通信与 `.HMI` 工程。
- 设备 PIN 流程的真实交互（模拟器默认关闭 PIN）。
- 长时间运行、Flash 磨损、掉电恢复。
- `tools/deploy.py` 在真实板端的上传/重置。

以上项在对应硬件/工程完成后补测，未测项不得写成「已通过」。
