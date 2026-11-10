# 图片与标志

## Open Source Software 徽标

`oss-badge.svg` 是 README 顶部的软件开源徽标，标注 **OPEN SOURCE SOFTWARE · MIT**。

- 本项目自制徽标，不使用 OSI 官方标志，也不暗示 OSI 认证；
- 软件许可证为 MIT，属于 OSI 认可的许可证；
- 徽标随本项目文档按 MIT 使用，可修改颜色/文字。

## OSHW 齿轮标志

`oshw-logo.svg` 是 README 顶部的 Open Source Hardware 齿轮标志。

- 原始标志：Open Source Hardware Association (OSHWA)
- 清洁矢量版：timmwille / osh-logo
- 来源：https://github.com/timmwille/osh-logo
- 许可证：CC BY-SA 4.0
- 用途：标识本项目的 open hardware 属性，不代表 OSHWA 认证；本项目没有 OSHWA UID。

该标志不是 CERN-OHL-S-2.0 或 MIT 的一部分；再分发时请保留本署名和 CC BY-SA 4.0 链接。

## 已使用的实拍图

以下图片由 `Picture/` 中的原始照片压缩生成（最长边 1600px），用于 README 内嵌展示：

| 文件 | 画面 | README 位置 |
|---|---|---|
| `overview.jpg` | 设备、绿植、TFT、按钮、继电器、水泵整体 | 标题下方 |
| `tft-dashboard.jpg` | ILI9341 竖屏仪表盘特写 | 硬件清单 |
| `breadboard-wiring.jpg` | ESP32-S3 面包板与 SPI/I²C/按钮接线 | 引脚分配 |
| `irrigation-test.jpg` | 低压泵从水杯抽水到种植盆 | 灌溉安全模型 |

## 截图占位

以下位置已经预留在 README 对应章节，截图后放入本目录并替换文字块：

| 文件 | 画面 | README 位置 |
|---|---|---|
| `web-overview.png` | Web 总览页、环境曲线、节气卡片 | Web 管理页 |
| `web-irrigation.png` | 灌溉/设置页、阈值与标定 | Web 管理页 |
| `mcp-tools.png` | MCP 客户端调用工具 | MCP Server |

## 替换截图

1. 将截图放到本目录，文件名与上表一致；
2. 在根目录 `README.md` 中找到对应的 `> **截图占位 ...**` 文字块；
3. 删除文字块，换成：

```markdown
![截图说明](docs/images/文件名.png)
```

截图不要包含 Wi-Fi 密码、PIN、Token 或其他敏感信息。
