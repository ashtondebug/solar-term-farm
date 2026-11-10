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

## 项目图片占位

README 中的项目图库目前使用文字占位，上传真实图片后按下面文件名替换。

| 编号 | 建议文件 | 画面内容 | README 位置 |
|---|---|---|---|
| 01 | `01-overview.jpg` | 设备、TFT、按钮、继电器、水泵整体 | 项目图库 |
| 02 | `02-tft-dashboard.jpg` | 竖屏 TFT 仪表盘正视图 | 项目图库 |
| 03 | `03-web-dashboard.png` | Web 管理页总览 | 项目图库 |
| 04 | `04-wiring.jpg` | ESP32-S3、TFT、传感器、继电器接线 | 项目图库 |
| 05 | `05-mcp-client.png` | MCP 客户端调用工具 | 项目图库 |
| 06 | `06-irrigation-test.jpg` | 水泵/继电器/按钮测试 | 项目图库 |

## 替换步骤

1. 将图片放到本目录，文件名与上表一致；
2. 在根目录 `README.md` 中找到对应的 `> **图片占位 ...**` 文字块；
3. 删除文字块，换成：

```markdown
![图片说明](docs/images/文件名.jpg)
```

图片建议不超过 1600px 宽；JPG/PNG 均可。不要提交包含 Wi-Fi 密码、PIN 或其他敏感信息的截图。
