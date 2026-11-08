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
                 "history":[]},
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

返回 24 条元数据与当前节气。长文案未补齐的条目 `available=false`。

### GET /api/v1/config

返回公开配置；不包含 PIN、Wi-Fi 密码。

### PUT /api/v1/config

请求体接受 `irrigation`、`plant` 与 `calibration` 三个 section：

```json
{"irrigation":{"mode":"manual","soil_threshold":35,"max_run_s":20,"min_interval_s":1800},
 "plant":{"profile":"general"},
 "calibration":{"soil_dry":18000,"soil_wet":9000}}
```

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
