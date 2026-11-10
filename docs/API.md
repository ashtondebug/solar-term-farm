# HTTP API（/api/v1）

## 1. 通用约定

- 仅局域网访问，由 ESP32-S3 提供；不依赖云。
- 请求/响应 `Content-Type: application/json; charset=utf-8`。
- 成功：

```json
{"ok": true, "data": {}, "ts": 1762500000}
```

- 失败：

```json
{"ok": false, "error": {"code": "INVALID_CONFIG", "message": "..."}, "ts": 1762500000}
```

- 时间戳为 Unix 秒（UTC）。设备时间未同步时，`device.time_synced=false`。
- 控制类请求需要 `X-AgriVerse-Pin`（当 `security.require_pin=true`）。
- 控制请求必须带 `request_id`；同一 ID 在 60 秒内幂等。
- 单请求 body ≤ 4KB；请求超时 5 秒。

## 2. 端点

### GET /api/v1/state

返回全量快照。核心字段：

```json
{
  "device": {"name":"AgriVerse","version":"0.1.0","model":"ESP32-S3 N16R8",
             "firmware":"MicroPython","uptime_s":123,"time_synced":true,
             "now":1762500000,"now_local":"2026-11-07T20:00:00+08:00",
             "source":"device"},
  "sensors": {
    "soil":   {"value":42.0,"unit":"%","valid":true,"ts":1762500000,"error":null,"raw":18068,"status":"ok"},
    "air_temp": {"value":24.6,"unit":"C","valid":true,"ts":1762500000,"error":null,"status":"ok"},
    "air_humidity": {"value":63.0,"unit":"%","valid":true,"ts":1762500000,"error":null,"status":"ok"},
    "light": {"value":12680.0,"unit":"lx","valid":true,"ts":1762500000,"error":null,"status":"ok"}
  },
  "suitability": {"score":82,"status":"good","components":{"soil":70,"temp":90,"humidity":82,"light":86},
                  "reasons":[],"ts":1762500000},
  "solar_term": {"name":"立冬","index":18,"season":"冬季","angle":225,"start_ts":...,"end_ts":...},
  "irrigation": {"mode":"auto","pump":false,"state":"idle","remaining_s":0,
                 "last_start_ts":null,"last_stop_ts":null,"max_run_s":20,"threshold":35.0,
                 "alarm":null,"relay_feedback":null,"history":[]},
  "network": {"wifi":"connected","status":"connected","ssid":"...","ip":"192.168.1.50","rssi":-55},
  "security": {"pin_required": false},
  "config": {"irrigation": {}, "plant": {}, "calibration": {"soil_dry": null, "soil_wet": null}, "sampling": {}, "device": {}},
  "meta": {"source":"device","ts":1762500000}
}
```

- 传感器 `valid=false` 时 `value` 为 `null`，`error` 说明原因（`uncalibrated`、`crc_error`、`stale` 等）。
- `sensors.soil.raw` 是 ADC 原始计数，仅用于干湿两点标定，不是湿度百分比。
- 适宜度在数据无效/过期时 `score=null`、`status="unavailable"`。
- `meta.source` 为 `device` 或 `simulator`（仅开发模拟器）。

### GET /api/v1/history?range=12h|24h|7d

返回历史点数组：

```json
{"range":"12h","points":[{"ts":1762500000,"temp":24.6,"humidity":63,"soil":42,"light":12680,"suitability":82}]}
```

无效 range 返回 400 `BAD_RANGE`。

### GET /api/v1/solar-terms

返回 24 条元数据以及 `name/season/angle/date_hint/intro/proverbs/customs/tips/available/index`。设备端由构建生成的 `solar-terms.json` 直接返回，避免在板端构造大 JSON。

### GET /api/v1/plant-profiles

返回内置与导入档案的 `key`、`name`、`builtin`、`stages`，以及阶段列表。

### POST /api/v1/plant-profiles/import

导入一个或一组植物档案。请求体格式见 `docs/plant-profiles.example.json`：

```json
{"version":1,"plants":[{"key":"my-tomato","name":"我的番茄","stages":{
  "seedling":{"ranges":{
    "soil_moisture":[55,70],"air_temp":[18,24],"air_humidity":[60,80],
    "light":[8000,20000],"soil_temp":[16,22]},
   "weights":{"soil_moisture":0.35,"air_temp":0.3,"air_humidity":0.15,"light":0.2}
  }}}]}
```

- 档案保存在设备 `/data/plants.json`，重启后自动加载；同名导入档案覆盖旧版本。
- 内置 key（`general/lettuce/tomato/strawberry`）不可覆盖。
- 每个阶段至少需要 `soil_moisture`、`air_temp`、`air_humidity`、`light` 四项范围；`weights` 可省略，省略时四项等权。
- `soil_temp` 会保存为档案元数据，但当前硬件没有土壤温度传感器，不参与评分。
- 可选 `traits` 保存整株特性（株型、根系、根深、授粉、病害、光周期、水分策略等），用于“农事建议”展示；其中 `reviewed/control_eligible` 默认 false。

### GET /api/v1/config

返回公开配置；不包含 PIN、Wi-Fi 密码。

### PUT /api/v1/config

请求体接受 `irrigation`、`plant` 与 `calibration` 三个 section：

```json
{"irrigation":{"mode":"manual","soil_threshold":35,"max_run_s":20,"min_interval_s":1800},
 "plant":{"profile":"tomato","stage":"flowering",
          "weights":{"soil":0.4,"temp":0.3,"humidity":0.1,"light":0.2}},
 "calibration":{"soil_dry":18000,"soil_wet":9000}}
```

- `plant.profile`：`general` / `lettuce` / `tomato` / `strawberry`；`plant.stage`：`seedling` / `growth` / `flowering` / `harvest`。
- `plant.weights` 可省略或为 `null`，使用档案/阶段默认权重；填写时四项必须是 0–1 且总和大于 0。
- `tft` 配置 2.8 英寸 ILI9341：`{"enabled":true,"rotation":3,"freq":20000000,"width":240,"height":320}`；SCK=GPIO40、SDA=GPIO39、RST=GPIO38、DC=GPIO2、CS=GPIO1，竖屏常亮显示环境、水泵和节气。
- `button` 配置 GPIO41 按钮：`{"enabled":true,"active_high":true,"debounce_ms":50}`；按一次启动，再按一次停止；停泵后 5 秒内再按会排队到 `min_off_s` 结束，不直接操作继电器。

- `calibration.soil_dry` / `soil_wet` 是 ADC 原始计数（0–65535），必须同时设置或同时为 `null`；差值至少 500。
- 标定保存后，下一轮传感器采样生效；`GET /api/v1/state` 的 `sensors.soil.raw` 可用于“读取当前值”。
- 校验失败返回 422 `INVALID_CONFIG`，不会部分保存。
- 成功后返回公开配置。

### POST /api/v1/irrigation/commands

```json
{"action":"start","request_id":"web-1762500000-abc"}
```

- `action`：`start` / `stop`。
- 缺 `request_id` 返回 400 `MISSING_REQUEST_ID`。
- 继电器故障、最小停泵未到、已运行等返回 409，`error.code` 为 `FAULT` / `MIN_OFF` / `ALREADY_RUNNING`。
- 返回 `{"irrigation": {...}, "request_id": "..."}`。

### POST /api/v1/time

```json
{"epoch":1762500000}
```

浏览器打开页面时，如果设备 `time_synced=false`，会自动调用一次。时间范围 2020–2100，越界返回 400。

### GET /api/v1/health

轻量探活，不鉴权：

```json
{"version":"0.1.0","uptime_s":123,"now":1762500000}
```

## 3. 错误码

| code | HTTP | 含义 |
|---|---:|---|
| `PIN_REQUIRED` | 401 | 需要 PIN |
| `PIN_INVALID` | 401 | PIN 错误 |
| `BAD_RANGE` | 400 | 历史范围非法 |
| `BAD_ACTION` | 400 | action 不是 start/stop |
| `MISSING_REQUEST_ID` | 400 | 缺少幂等 ID |
| `INVALID_CONFIG` | 422 | 配置校验失败 |
| `NOT_FOUND` | 404 | 未知端点 |
| `FAULT` / `MIN_OFF` / `ALREADY_RUNNING` | 409 | 安全约束拒绝 |
| `INTERNAL` | 500 | 设备内部错误 |

## 4. 实现位置

- `ESP/web/api.py`：路由、校验、鉴权、envelope。
- `ESP/web/server.py`：HTTP/1.1 解析、静态文件、超时与大小限制。
- `docs/API.md` 与实现不一致时以代码与测试为准；修改 API 必须同步本文件与 `tests/test_api.py`。
