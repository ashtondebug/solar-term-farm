# 控件与变量表（逻辑名，待 USART HMI 落地）

> 这里的名称是设备端同步逻辑名，不代表已经核实的 TJC 变量/指令语法。实际控件 ID、变量名、字库 ID 必须在上位机与 Wiki 中确认。

## 1. 页面与控件

| 页面 | 控件 | 逻辑 ID | 类型 | 说明 |
|---|---|---|---|---|
| 0 主页 | 时间 | `date_text` | 文本 | `YYYY-MM-DD HH:MM` |
| 0 | 节气 | `term_name` | 文本 | 当前节气 |
| 0 | 空气温度 | `temp_value` | 数值 | °C，1 位小数 |
| 0 | 空气湿度 | `hum_value` | 数值 | %，整数 |
| 0 | 土壤湿度 | `soil_value` | 数值 | %，整数；未标定显示 `--` |
| 0 | 光照 | `lux_value` | 数值 | lx，整数 |
| 0 | 适宜度 | `score_value` | 数值 | 0–100；无数据显示 `--` |
| 0 | 泵状态 | `pump_state` | 文本 | 运行/停止/故障 |
| 0 | Wi-Fi | `wifi_state` | 文本 | 已连接/连接中/配网中/离线 |
| 1 节气 | 名称 | `term_title` | 文本 | 当前选中节气 |
| 1 | 黄经 | `term_angle` | 文本 | 如 `225°` |
| 1 | 简介 | `term_intro` | 文本 | 多行，注意溢出 |
| 1 | 农谚 | `term_proverb` | 文本 | 传统经验参考 |
| 1 | 习俗 | `term_custom` | 文本 | 2 条以内 |
| 1 | 农事 | `term_tip` | 文本 | 2 条以内 |
| 2 环境 | 四项读数 | `env_*` | 文本/数值 | 名称、值、状态 |
| 2 | 更新时间 | `env_updated` | 文本 | 设备时间 |
| 3 灌溉 | 模式 | `pump_mode` | 文本 | 自动/手动 |
| 3 | 泵状态 | `pump_state_big` | 文本 | 大字 |
| 3 | 运行秒数 | `run_seconds` | 数值 | 0–120 |
| 3 | 启动/停止 | `btn_start` / `btn_stop` | 按钮 | 触摸事件 |
| 4 设置 | SSID | `ssid_text` | 文本 | 当前网络 |
| 4 | IP | `ip_text` | 文本 | 局域网 IP |
| 4 | 密码 | `pass_input` | 文本输入 | 掩码显示，不回显 |
| 4 | 扫描 | `btn_scan` | 按钮 | 触发扫描 |
| 4 | 连接 | `btn_connect` | 按钮 | 提交连接意图 |
| 4 | 重新配网 | `btn_reprovision` | 按钮 | 清除旧配置前先验证新网络 |

## 2. 设备端字段映射

| 屏幕逻辑名 | `/api/v1/state` 字段 |
|---|---|
| `date_text` | `device.now_local` |
| `term_name` | `solar_term.name` |
| `temp_value` | `sensors.air_temp.value` |
| `hum_value` | `sensors.air_humidity.value` |
| `soil_value` | `sensors.soil.value` |
| `lux_value` | `sensors.light.value` |
| `score_value` | `suitability.score` |
| `pump_state` | `irrigation.pump` / `irrigation.state` |
| `pump_mode` | `irrigation.mode` |
| `run_seconds` | `irrigation.remaining_s`（或已运行秒数） |
| `wifi_state` | `network.status` |
| `ip_text` | `network.ip` |

## 3. 刷新策略

- 主页：1 秒刷新一次状态文本/数值；只在值变化时发送。
- 环境：2 秒；节气页：进入时刷新 + 60 秒。
- 灌溉：1 秒；按钮点击后立即回写设备状态。
- 设置：进入时刷新；扫描结果按用户操作返回。
- 断线：显示「屏幕与设备通信中断」，不显示旧数据为实时。

## 4. 触摸事件

| 控件 | 设备动作 | 安全约束 |
|---|---|---|
| `btn_start` | `POST /api/v1/irrigation/commands`（start） | 设备端最长运行、故障锁存、PIN（若启用） |
| `btn_stop` | 同上（stop） | 立即停止优先 |
| `btn_scan` | 设备扫描 Wi-Fi | 不阻塞主循环 |
| `btn_connect` | 设备连接新网络 | 验证成功后才替换旧配置 |
| 模式切换 | `PUT /api/v1/config` | 参数校验 |

## 5. 待确认

- 控件 ID 与变量名的实际语法。
- 文本控件最大字符数与中文字库 ID。
- 曲线控件是否可用、通道数。
- 触摸事件返回格式与控件 ID 对应关系。
