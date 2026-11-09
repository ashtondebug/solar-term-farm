# AgriVerse TJC 5 页 HMI 模板

适用屏幕：TJC3224T128_011R_A01（240×320 竖屏）  
模板只建一次；之后 ESP32 通过 UART 更新组件，不再改 HMI 工程。  
当前实测：9600 baud、5V TTL；ESP32 接入前必须加 3.3V↔5V 电平转换。

## 1. 工程设置

新建工程时选择：

- 型号：TJC3224T128_011R_A01
- 分辨率：240×320
- 方向：竖屏
- 波特率：9600
- 页面：`overview`、`environment`、`irrigation`、`settings`、`wifi`

`Program.s` 建议内容：

```text
baud=9600
dim=100
page overview
```

字体建议在 HMI 里建三套：

| 字体 | 字号 | 用途 |
|---|---|---|
| `font0` | 10 | 标签、状态栏 |
| `font1` | 14 | 正文/按钮 |
| `font2` | 24 | 大数值 |

颜色：

```text
深绿 #173D32   浅底 #F5F7F4
绿色 #3C8B68   蓝色 #4E8FB5
深棕 #8C5A3C   琥珀 #E6A100
红色 #C65C4E   灰色 #7C897F
```

所有组件背景尽量用浅底/透明，文字颜色按语义设置。

## 2. 公共布局

### 顶栏（每页都放）

| 组件 | 类型 | x | y | w | h | 字体 | 文本/说明 |
|---|---|---|---|---|---|---|---|
| `t_title` | 文本 | 8 | 6 | 92 | 20 | font1 | 页面标题 |
| `t_wifi` | 文本 | 102 | 6 | 52 | 20 | font0 | WiFi 状态 |
| `t_time` | 文本 | 160 | 6 | 72 | 20 | font0 | 时间 |
| `t_auth` | 文本 | 8 | 24 | 80 | 16 | font0 | 已解锁/只读 |

### 底部导航（每页都放，y=282）

| 组件 | 类型 | x | y | w | h | 文本 |
|---|---|---|---|---|---|---|
| `b_nav_overview` | 按钮 | 0 | 282 | 48 | 38 | 总览 |
| `b_nav_env` | 按钮 | 48 | 282 | 48 | 38 | 环境 |
| `b_nav_irr` | 按钮 | 96 | 282 | 48 | 38 | 灌溉 |
| `b_nav_set` | 按钮 | 144 | 282 | 48 | 38 | 设置 |
| `b_nav_wifi` | 按钮 | 192 | 282 | 48 | 38 | WiFi |

按钮事件代码见第 8 节。页面内容区使用 `y=44..278`。

## 3. overview（总览）

内容区：

| 组件 | 类型 | x | y | w | h | 字体 | 说明 |
|---|---|---|---|---|---|---|---|
| `t_temp` | 文本 | 8 | 58 | 108 | 30 | font2 | 空气温度 |
| `t_hum` | 文本 | 124 | 58 | 108 | 30 | font2 | 空气湿度 |
| `t_soil` | 文本 | 8 | 112 | 108 | 30 | font2 | 土壤湿度 |
| `t_light` | 文本 | 124 | 112 | 108 | 30 | font2 | 光照 |
| `t_score` | 文本 | 8 | 166 | 70 | 36 | font2 | 适宜度分数 |
| `t_pump` | 文本 | 96 | 166 | 70 | 22 | font1 | 运行/停止 |
| `t_mode` | 文本 | 96 | 192 | 70 | 22 | font1 | 自动/手动 |
| `t_term` | 文本 | 8 | 214 | 224 | 22 | font1 | 当前节气 |
| `t_status` | 文本 | 8 | 246 | 224 | 28 | font0 | 最近操作结果 |

可选静态标签：温度、湿度、土壤、光照、适宜度。

## 4. environment（环境）

保留同样的四个数据组件（同名组件在当前页面生效）：

| 组件 | 类型 | x | y | w | h | 字体 |
|---|---|---|---|---|---|---|
| `t_temp` | 文本 | 8 | 58 | 108 | 30 | font2 |
| `t_hum` | 文本 | 124 | 58 | 108 | 30 | font2 |
| `t_soil` | 文本 | 8 | 112 | 108 | 30 | font2 |
| `t_light` | 文本 | 124 | 112 | 108 | 30 | font2 |
| `t_score` | 文本 | 8 | 160 | 70 | 32 | font2 |
| `t_env_note` | 文本 | 8 | 200 | 224 | 52 | font0 |
| `t_status` | 文本 | 8 | 246 | 224 | 28 | font0 |

`t_env_note` 初始文本：

```text
趋势图请在 Web 端查看。
本页显示当前实时值。
```

## 5. irrigation（灌溉）

| 组件 | 类型 | x | y | w | h | 字体 | 说明 |
|---|---|---|---|---|---|---|---|
| `t_pump` | 文本 | 8 | 48 | 108 | 24 | font2 | 运行/停止 |
| `t_mode` | 文本 | 124 | 48 | 108 | 24 | font2 | 自动/手动 |
| `t_remain` | 文本 | 8 | 80 | 108 | 20 | font1 | 剩余时间 |
| `t_state` | 文本 | 124 | 80 | 108 | 20 | font1 | 状态 |
| `t_threshold` | 文本(键盘) | 8 | 112 | 224 | 28 | font1 | 土壤阈值，键盘输入 |
| `t_pin_input` | 文本(键盘/密码) | 8 | 148 | 224 | 28 | font1 | PIN 输入 |
| `b_auth` | 按钮 | 8 | 184 | 108 | 30 | font1 | 解锁 |
| `b_start` | 按钮 | 124 | 184 | 108 | 30 | font1 | 启动 |
| `b_stop` | 按钮 | 8 | 220 | 108 | 30 | font1 | 停止 |
| `b_mode` | 按钮 | 124 | 220 | 108 | 30 | font1 | 自动/手动 |
| `t_status` | 文本 | 8 | 252 | 224 | 26 | font0 | 结果 |

> 底部导航固定在 y=282，因此灌溉页内容按钮不能放到 282 以下。

## 6. settings（设置）

| 组件 | 类型 | x | y | w | h | 字体 | 说明 |
|---|---|---|---|---|---|---|---|
| `t_ip` | 文本 | 8 | 52 | 224 | 20 | font0 | 设备 IP |
| `t_pin` | 文本 | 8 | 78 | 224 | 28 | font2 | PIN 显示 |
| `t_pin_input` | 文本(键盘/密码) | 8 | 112 | 224 | 30 | font1 | PIN 输入 |
| `b_auth` | 按钮 | 8 | 148 | 108 | 34 | font1 | 解锁 |
| `b_pin_show` | 按钮 | 124 | 148 | 108 | 34 | font1 | 显示 PIN |
| `b_nav_wifi` | 按钮 | 8 | 188 | 224 | 34 | font1 | 进入 WiFi 配网 |
| `t_status` | 文本 | 8 | 228 | 224 | 30 | font0 | 结果 |

## 7. wifi（配网）

| 组件 | 类型 | x | y | w | h | 字体 | 说明 |
|---|---|---|---|---|---|---|---|
| `t_wifi_detail` | 文本 | 8 | 44 | 108 | 22 | font1 | 状态（配网页专用） |
| `t_wifi_count` | 文本 | 124 | 44 | 108 | 22 | font0 | 数量 |
| `t_wifi0` | 文本 | 8 | 70 | 224 | 20 | font0 | 第 1 个 |
| `t_wifi1` | 文本 | 8 | 92 | 224 | 20 | font0 | 第 2 个 |
| `t_wifi2` | 文本 | 8 | 114 | 224 | 20 | font0 | 第 3 个 |
| `t_wifi3` | 文本 | 8 | 136 | 224 | 20 | font0 | 第 4 个 |
| `t_wifi4` | 文本 | 8 | 158 | 224 | 20 | font0 | 第 5 个 |
| `t_wifi5` | 文本 | 8 | 180 | 224 | 20 | font0 | 第 6 个 |
| `t_ssid` | 文本(键盘) | 8 | 204 | 224 | 24 | font0 | SSID |
| `t_password` | 文本(键盘/密码) | 8 | 230 | 224 | 24 | font0 | 密码 |
| `b_scan` | 按钮 | 8 | 258 | 108 | 20 | font0 | 扫描 |
| `b_connect` | 按钮 | 124 | 258 | 108 | 20 | font0 | 连接 |

> 密码组件设置 `pw=1`，SSID/密码设置键盘输入；屏幕不回显密码。

## 8. 按钮事件代码

以下命令都以换行结尾。USART HMI 的 `prints` 拼接语法以你当前 1.68.x 版本为准；若不支持多项拼接，就拆成多次 `prints`。

### 页面导航

```text
page overview
prints "PAGE|overview"
printh 0a
```

把 `overview` 换成 `environment`、`irrigation`、`settings`、`wifi`。

### 解锁

```text
prints "AUTH|"
prints t_pin_input.txt
printh 0a
```

### 显示 PIN

```text
prints "PIN|SHOW"
printh 0a
```

### 启停

```text
prints "CMD|start"
printh 0a
```

```text
prints "CMD|stop"
printh 0a
```

### 模式

```text
prints "MODE|auto"
printh 0a
```

```text
prints "MODE|manual"
printh 0a
```

### 设置阈值

```text
prints "SET|soil_threshold|"
prints t_threshold.txt
printh 0a
```

### WiFi 扫描

```text
prints "WIFI|SCAN"
printh 0a
```

### WiFi 连接

```text
prints "WIFI|CONNECT|"
prints t_ssid.txt
prints "|"
prints t_password.txt
printh 0a
```

### PING（联调）

```text
prints "PING"
printh 0a
```

## 9. 导入与测试

1. HMI 编译并下载到屏幕；
2. 屏幕独立 5V 供电；
3. USB-TTL 的 9600 串口调试；
4. 先发 `PING`，确认 ESP32 返回 `t_status.txt="PONG"`；
5. 接 ESP32 前加电平转换；
6. Web/API 设置：

```json
{"display":{"enabled":true,"baudrate":9600}}
```

7. 重启 ESP32，屏幕应显示实时值；
8. 测试 `AUTH` → `CMD|start` → `CMD|stop`，确认水泵只由控制器动作。

## 10. 注意事项

- 同名组件（如 `t_temp`）可分布在多个页面；TJC 命令作用于当前页面；
- 如果 USART HMI 不允许跨页同名，请把页面数据组件改成 `o_temp`/`e_temp`，并同步修改 `screen.py`；
- PIN 输入框与 PIN 显示框分开：`t_pin_input` 输入，`t_pin` 显示；
- WiFi 密码只写 `/data/wifi.json`，不显示明文；
- 屏幕断线不改变水泵状态，ESP32 仍按控制器安全逻辑运行。
