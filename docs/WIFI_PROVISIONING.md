# Wi-Fi 配网状态机（M3A）

设备端已经实现扫描、连接、验证、保存与 5 次失败转配网的服务层；配网入口由 Web 页面提供。所有状态变化都在非阻塞 `tick()` 中推进，断网不影响传感器与灌溉。

## 1. 状态

| 状态 | 含义 |
|---|---|
| `unconfigured` | 没有已保存的 SSID |
| `idle` | 有已保存配置，等待连接 |
| `connecting` | 已发起连接，等待结果或超时（20 秒） |
| `connected` | 已获取 IP |
| `failed` | 本次连接失败，等待下一次重试（15 秒间隔） |
| `provisioning` | 连续 5 次失败，停止自动重试，等待用户重新配网 |

## 2. 规则

- `start()`：有已保存配置才尝试连接；否则进入 `unconfigured`。
- 自动重试：每次失败后间隔 15 秒，最多 5 次；达到上限进入 `provisioning`。
- 连接超时 20 秒；错误码 1002/1003/1004 分别记录为 `wrong_password` / `no_ap_found` / `connect_failed`。
- 手动 `connect(ssid, password)`：立即开始一次尝试，**验证成功后才写 `/data/wifi.json`**；旧配置在新网络验证成功前保持不变。
- `cancel_provisioning()`：放弃待验证的新网络，恢复到已保存网络。
- `forget()`：显式清除已保存配置并断开；需要用户明确确认后调用。
- 设备断网不影响采集、适宜度和自动灌溉。

## 3. 安全

- Wi-Fi 密码只保存在 `/data/wifi.json`，原子写；不通过 `/api/v1/state` 返回。
- `status()` 只返回 `ssid`、`saved_ssid`、`pending_ssid`、IP、RSSI、attempts、last_error；不返回密码。
- 日志不打印密码；`connect` 的异常信息也不包含密码。
- ESP32 无安全元件，物理接触 Flash 可读；这是已记录的限制。
- 重新配网时先验证新网络，再替换旧配置；不先删除旧配置。

## 4. 接口

```text
NetworkManager.scan(limit=20) -> [{ssid, rssi, security, secure}]
NetworkManager.connect(ssid, password) -> (ok, error_code)
NetworkManager.cancel_provisioning() -> bool
NetworkManager.forget() -> None
NetworkManager.status() -> dict
NetworkManager.tick(now) -> None
```

`scan()` 会去重同名 SSID，保留最强 RSSI，按 RSSI 降序，最多 20 条；空 SSID 跳过。

## 5. 测试

`tests/test_network.py` 覆盖：

- 未配置状态；
- 连接成功后才保存；
- 密码不出现在 `status()`；
- 错误密码重试 5 次后进入 `provisioning`；
- 取消配网恢复旧网络；
- 扫描去重/排序；
- `WifiStore` 原子写入与清除。

运行：

```bat
python -m unittest discover -s tests -p "test_network.py" -v
```

## 6. 配网界面

当前由 Web 设置页提供扫描、SSID、密码、连接状态、IP 和重新配网；不再维护 TJC 屏幕配网页。

## 7. 待办

- 首次配网与重新配网的完整流程测试；
- 真机 Wi-Fi 射频与 5 次失败实际验证。
