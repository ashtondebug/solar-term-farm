# AgriVerse 串口屏协议与 HMI 页面规范

适用屏幕：TJC3224T128_011R_A01（3.2 寸级，具体以模块资料为准）  
当前实测：USB-TTL `COM3`，屏幕 UART **9600 baud**，5V TTL  
固件入口：`ESP/display/`

> 重要：屏幕 UART 是 5V TTL，ESP32-S3 是 3.3V。接 ESP32 前必须使用
> TXS0108E / BSS138 双向电平转换，并共地；屏幕用独立 5V 供电。

## 1. 页面

在 USART HMI 中建立以下页面，页面名必须一致：

| 页面 | 用途 |
|---|---|
| `boot` | 启动、版本、等待通信 |
| `overview` | 总览：温湿度、土壤、光照、适宜度、水泵、节气 |
| `environment` | 环境趋势/传感器详情 |
| `irrigation` | 灌溉模式、启停、阈值、剩余时间 |
| `settings` | PIN、IP、设备信息、进入配网 |
| `wifi` | WiFi 扫描、SSID、密码、连接状态 |

## 2. 组件命名

固件只更新这些组件；页面可以自行排版，但组件名不要改。

### 全局/状态

| 组件 | 类型 | 内容 |
|---|---|---|
| `t_status` | 文本 | 最近一次操作结果/错误 |
| `t_auth` | 文本 | `已解锁` / `只读` |
| `t_page` | 文本 | 当前页面名 |
| `t_time` | 文本 | 设备本地时间 |
| `t_fault` | 文本 | 故障提示，空字符串表示正常 |

### 总览

| 组件 | 类型 | 内容 |
|---|---|---|
| `t_temp` | 文本 | 空气温度 |
| `t_hum` | 文本 | 空气湿度 |
| `t_soil` | 文本 | 土壤湿度 |
| `t_light` | 文本 | 光照 |
| `t_score` | 文本 | 适宜度分数 |
| `t_pump` | 文本 | `运行` / `停止` |
| `t_mode` | 文本 | `自动` / `手动` |
| `t_remain` | 文本 | 剩余运行秒数 |
| `t_state` | 文本 | `idle/manual/auto/cooldown/fault` |
| `t_term` | 文本 | 当前节气 |

### 网络/设置

| 组件 | 类型 | 内容 |
|---|---|---|
| `t_wifi` | 文本 | WiFi 状态中文（顶栏） |
| `t_wifi_detail` | 文本 | WiFi 状态（配网页专用，避免同名冲突） |
| `t_ip` | 文本 | 设备 IP |
| `t_pin` | 文本 | PIN（仅 `PIN|SHOW` 后显示） |
| `t_pin_input` | 文本（密码/键盘） | PIN 输入，不与显示框复用 |
| `t_threshold` | 文本 | 土壤阈值 |
| `t_wifi_count` | 文本 | 扫描到的 WiFi 数量 |
| `t_wifi0`…`t_wifi5` | 文本 | SSID + RSSI |

## 3. 屏幕 → ESP32 命令

屏幕按钮通过串口发送一行 ASCII 文本（换行结尾）：

```text
PING
AUTH|123456
PAGE|overview
CMD|start
CMD|stop
MODE|auto
MODE|manual
SET|soil_threshold|35
WIFI|SCAN
WIFI|CONNECT|MyWiFi|password
PIN|SHOW
```

说明：

- `AUTH` 成功后 300 秒内可执行写操作；
- `CMD`/`MODE`/`SET`/`WIFI|CONNECT`/`PIN|SHOW` 需要先 `AUTH`（如果启用了 PIN）；
- `WIFI|SCAN` 是只读操作；
- SSID 不能包含 `|`；密码可以包含 `|`，解析器会保留到行尾；
- 未知命令只更新 `t_status`，不会执行；
- 不要把密码写入日志或屏幕历史。

## 4. ESP32 → 屏幕

固件使用 TJC 组件命令，每条命令以 `FF FF FF` 结尾：

```text
t_status.txt="已执行"
t_temp.txt="16.5"
t_hum.txt="51"
t_soil.txt="100"
t_light.txt="529"
t_score.txt="45"
t_pump.txt="停止"
t_mode.txt="自动"
t_remain.txt="0s"
t_time.txt="09:08"
t_wifi.txt="已连接"
t_ip.txt="192.168.153.234"
t_term.txt="立冬"
page overview
```

`ScreenController` 会做去重：值未变化时不会重复发送。

## 5. HMI 按钮事件写法

USART HMI 的按钮事件中用 `prints` 发送文本。示例语义：

```text
// AUTH 按钮：读取 PIN 输入框后发送
prints "AUTH|", t_pin.txt

// 开始按钮
prints "CMD|start"

// 停止按钮
prints "CMD|stop"

// 扫描 WiFi
prints "WIFI|SCAN"

// 连接 WiFi（SSID、密码来自输入框）
prints "WIFI|CONNECT|", t_ssid.txt, "|", t_password.txt
```

具体 `prints` 拼接语法以你当前 USART HMI 版本为准；如果版本不支持多项拼接，可以用多个 `prints` 依次输出，最后输出换行。

页面切换建议在 HMI 本地执行 `page overview` 等，同时发送：

```text
PAGE|overview
```

这样 ESP32 能知道当前页面，便于后续做按页刷新。

## 6. PIN 与安全

- PIN 来自设备配置 `security.pin`，6 位数字；
- 默认 `require_pin=false`，屏幕只读也能用；
- 启用 PIN 后，写操作必须 `AUTH`；
- `PIN|SHOW` 只在已授权会话中显示，显示后不要长期停留在屏幕；
- 屏幕重启后重新进入只读，必须重新 `AUTH`；
- 屏幕断线不会触发任何水泵动作；
- 启动水泵仍由 `IrrigationController` 执行 `max_run_s`、`min_off_s` 等保护。

## 7. WiFi 配网

- `WIFI|SCAN` 返回最多 6 个 SSID；
- 屏幕用 `t_wifi0`…`t_wifi5` 显示；
- 用户输入 SSID/密码后发送 `WIFI|CONNECT`；
- ESP32 调用现有 `NetworkManager.connect()`；
- **只有连接成功后才保存** `/data/wifi.json`；失败保留旧网络；
- 密码输入框使用隐藏输入，屏幕不显示明文；
- 屏幕不直接操作 WLAN 驱动。

## 8. 固件启用方式

默认 `display.enabled=false`，不会占用 UART。接好电平转换和屏幕后，通过 Web/API 设置：

```json
{"display":{"enabled":true,"baudrate":9600}}
```

重启后 `main.py` 创建 UART1（TX17/RX18）并启动 `ScreenController`。  
如果还没有 HMI 组件，屏幕不会显示有效内容，但 UART 仍会发送组件命令。

## 9. 当前实现文件

```text
ESP/display/protocol.py      # 行协议解析、HMI 文本命令编码
ESP/display/transport.py     # UART 缓冲、FF FF FF 发送
ESP/display/screen.py        # 状态推送、PIN、WiFi、灌溉命令
tests/test_display.py        # 68 项总测试中的显示协议测试
```

5 页模板的坐标、字体、颜色和按钮事件见：

**[HMI_TEMPLATE.md](HMI_TEMPLATE.md)**

## 10. 后续联调顺序

1. 在 USART HMI 建好页面和组件；
2. USB-TTL 只连屏幕，确认 9600 通信；
3. 接电平转换后再把 ESP32 接到屏幕；
4. 先用 `PING` / `AUTH` 验证协议；
5. 再验证只读总览；
6. 最后验证灌溉启停、PIN、WiFi 配网；
7. 记录屏幕拔插、ESP32 复位、WiFi 断开场景。
