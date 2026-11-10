# 贡献指南

感谢关注 **SolarTerm Farm（节气智农）**。这是一个以 ESP32-S3、MicroPython、局域网 Web 和 MCP 为核心的智能灌溉项目。提交代码、文档、测试、接线经验或问题复现都欢迎。

> 参与贡献即表示你同意你的贡献按对应对象许可证授权：软件为 [MIT License](LICENSE)，硬件设计源为 [CERN-OHL-S-2.0](LICENSE-HARDWARE)。

---

## 1. 先了解项目边界

在修改代码前，请先读：

- [README.md](README.md)：项目概览、快速开始、硬件与安全模型
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)：分层和任务模型
- [docs/GPIO_WIRING.md](docs/GPIO_WIRING.md)：引脚、继电器与传感器接线
- [docs/API.md](docs/API.md)：HTTP API 契约
- [docs/TEST_PLAN.md](docs/TEST_PLAN.md)：验收项与真机测试范围

### 不可破坏的规则

1. **继电器只能由 `ESP/irrigation/` 中的控制器操作。**  
   Web、MCP、按钮、测试和脚本都只能提交 `start` / `stop` 意图，不能直接写 GPIO5。

2. **安全约束不可绕过。**  
   `max_run_s`、`min_off_s`、故障锁存和请求幂等是设备端最终裁决，不能为了“方便测试”在客户端绕过。

3. **不得提交真实凭据。**  
   Wi-Fi 密码、PIN、Token、Cookie、私有 IP 配置不得进入提交、截图、日志或 issue。

4. **API 兼容性。**  
   `mcp__agriverse__*`、`X-AgriVerse-Pin` 和 `agriverse_mcp` 包名是兼容接口；重命名需要单独的迁移说明。

5. **TFT 只使用 ASCII 文本。**  
   当前 ILI9341 驱动使用内置 8×8 字体，不支持中文；不要在 TFT 绘制中文，否则会显示方块。

---

## 2. 开发环境

### 主机测试与模拟器

- Windows 10/11
- Python 3.11+
- 只运行模拟器时不需要安装第三方库

```bat
python -m unittest discover -s tests -v
python tools\build_web.py
python tools\devserver.py --port 8080 --open
```

### 固件

- ESP32-S3 N16R8
- MicroPython 1.29 或兼容版本
- `mpremote` / `esptool`

```bat
tools\install.bat
python tools\deploy.py --port COM11
```

### MCP Server

```powershell
cd mcp_server
.\install.ps1
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

---

## 3. 分支与提交

- 从 `main` 创建短分支：
  - `feat/tft-layout`
  - `fix/button-min-off`
  - `docs/contributing`
- 一个提交只做一件可审查的事。
- 提交信息建议使用 Conventional Commits：

```text
feat: add solar term card to TFT
fix: avoid full-screen redraw flicker
docs: document relay safety
test: cover button queued start
chore: update deploy script
```

- 不要提交：
  - `ESP/wifi_secrets.py`
  - `Touch_screen/HMI/` 下的本地 HMI/字体文件
  - 构建产物、日志、截图中的密钥
  - 真实设备 IP 或私人网络信息

提交前检查：

```bat
git status
git diff
git check-ignore -v ESP/wifi_secrets.py
```

---

## 4. 代码与文档规范

### Python / MicroPython

- 遵循 PEP 8 的可读子集；设备端避免大内存对象和长阻塞。
- 新增硬件行为时，必须同步：
  - `ESP/config.py` 默认值与校验
  - `docs/HARDWARE.md` / `docs/GPIO_WIRING.md`
  - `docs/API.md` 或 MCP 工具说明
  - 对应主机测试
- 任何新的传感器字段必须区分：
  - `value = null` 表示无效
  - `valid = false`
  - `error` 说明原因
  - `stale` 说明数据过期
- 不要用异常控制正常业务流；错误码保持稳定。

### Web

- 视觉源文件是根目录 `agriverse_admin_dashboard.html`、`app.js`、`app.css`。
- `ESP/web/static/` 是构建产物，由 `tools/build_web.py` 生成。
- 修改前端后至少运行：

```bat
python tools\build_web.py
node --check app.js
```

### TFT

- 240×320 竖屏布局。
- 使用 ASCII 标签，避免中文字库依赖。
- 优先局部刷新；不要每秒整屏 `fill`。
- 修改引脚或 `MADCTL` 时，同步记录到 `docs/GPIO_WIRING.md` 和测试记录。

### 文档

- 中文为主，命令、API 字段、代码标识符保持英文。
- 文档中的示例不要包含真实设备 IP、WiFi 密码或 PIN。
- 新增图片先放在 `docs/images/`，并在 README 中用相对路径引用。

---

## 5. 测试要求

### 最低要求

```bat
python -m unittest discover -s tests -v
```

当前基线：**69 项主机测试通过**。

MCP：

```powershell
cd mcp_server
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### 涉及以下改动时必须补测试

- 灌溉状态机、请求幂等、`MIN_OFF` / `MAX_RUN` / `FAULT`
- 配置迁移与默认值
- API 参数校验、错误码、鉴权
- 节气边界、植物档案导入
- TFT 格式化、按钮启停逻辑
- Wi-Fi 状态机

### 硬件相关改动

主机测试不能证明真实硬件安全。涉及继电器、水泵、TFT 供电或按钮接线时，PR 中请附：

- 接线变更说明
- 实测条件（电源、负载、串口日志）
- 失败/回滚方式
- 是否完成断电/复位状态检查

---

## 6. 硬件安全

- 继电器 IN 必须硬件下拉；水泵使用 COM/NO 常开触点。
- 水泵和继电器是感性负载：需要续流二极管、滤波和独立供电评估。
- 不得让水泵电流经过 ESP32 的 3.3V 稳压器。
- 调试泵时先断开负载，只测继电器；确认后再接水泵。
- TFT 供电不足、SPI 线过长或共地不良会导致闪烁、白屏或花屏；报告问题时请说明供电和接线。
- 不要通过软件绕过 `max_run_s` 或故障锁存来“测试泵”。

---

## 7. Pull Request 清单

提交 PR 前请确认：

- [ ] 改动范围单一，提交信息清晰
- [ ] 69 项主机测试通过（或说明新增/变更的测试）
- [ ] MCP 改动通过 `mcp_server/tests`
- [ ] 未提交 `ESP/wifi_secrets.py`、HMI/字体文件或真实凭据
- [ ] 已同步相关文档、引脚表和 API 说明
- [ ] 硬件改动附接线、供电与实测说明
- [ ] 没有绕过 `IrrigationController` 的安全约束
- [ ] TFT 文本仍为 ASCII

---

## 8. Issue 与安全报告

### 普通 Issue

请提供：

- 复现步骤
- 预期结果与实际结果
- 固件/工具版本
- 串口日志（隐藏 WiFi 密码、PIN、IP 后）
- 接线或供电说明（硬件问题）

### 安全漏洞

请不要在公开 Issue 中贴出 WiFi 密码、PIN、Token 或可被利用的细节。请通过仓库的 **GitHub Security Advisory** 私下报告，或先联系维护者。

---

## 9. 许可证

本项目采用双许可证：

| 对象 | 许可证 |
|---|---|
| 固件、Web、工具、测试、MCP | [MIT License](LICENSE) |
| 硬件设计文档、BOM、接线、装配 | [CERN-OHL-S-2.0](LICENSE-HARDWARE) |
| 第三方模块 | 各自厂商条款 |

```text
Software: MIT License
Copyright (c) 2026 AshtonDebug

Hardware: CERN Open Hardware Licence Version 2 - Strongly Reciprocal
```

提交软件贡献即表示你同意以 MIT 发布；提交硬件设计源即表示你同意以 CERN-OHL-S-2.0 发布。完整说明见 [docs/OPEN_HARDWARE.md](docs/OPEN_HARDWARE.md)。

本仓库尚未获得 OSHWA 认证 UID，不得声称“OSHW certified”或使用 OSHWA 认证标志。
