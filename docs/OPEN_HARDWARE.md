# Open Hardware 说明

SolarTerm Farm 以 **open source hardware** 方式发布：硬件设计源、BOM、装配说明和固件都可以获取、修改和再分发。

> **状态：OSHW-aligned / open hardware source available。**
> 本仓库**尚未申请 OSHWA 认证**，没有 OSHWA UID；在获得 UID 前不会使用 OSHWA 认证标志。

## 1. 许可证矩阵

| 对象 | 许可证 | 文件 |
|---|---|---|
| 硬件设计文档、BOM、接线、装配说明 | CERN-OHL-S-2.0 | [LICENSE-HARDWARE](../LICENSE-HARDWARE) |
| ESP32 固件、Web、工具、测试 | MIT | [LICENSE](../LICENSE) |
| MCP Server | MIT | [LICENSE](../LICENSE) |
| 第三方模块 | 各自厂商条款 | 不覆盖 |

CERN-OHL-S-2.0 是**强互惠**硬件许可证：修改并分发 Covered Source 或产品时，需要按同许可证提供 Complete Source。软件继续使用 MIT。

## 2. 设计源在哪里

| 设计内容 | 位置 |
|---|---|
| 物料清单 BOM | [hardware/BOM.csv](../hardware/BOM.csv) |
| 接线与装配 | [hardware/WIRING.md](../hardware/WIRING.md) |
| 引脚与电气约束 | [docs/GPIO_WIRING.md](GPIO_WIRING.md) |
| 硬件规格与限制 | [docs/HARDWARE.md](HARDWARE.md) |
| 固件 | [ESP/](../ESP/) |
| Web | 根目录 `agriverse_admin_dashboard.html`、`app.js`、`app.css` |
| MCP | [mcp_server/](../mcp_server/) |
| 测试 | [tests/](../tests/)、[mcp_server/tests/](../mcp_server/tests/) |

## 3. 设计范围

这是一个 **module-level build**，不是定制 PCB：

- ESP32-S3 N16R8 开发板；
- 2.8 英寸 ILI9341 SPI TFT；
- SHT31、BH1750、HW-390；
- GPIO41 按钮；
- 3.3V 高电平继电器；
- 低压直流水泵。

因此当前设计源是 BOM、接线、装配、固件和测试，而不是 KiCad/EasyEDA PCB 工程。若后续制作定制 PCB 或外壳，应把以下内容加入本仓库并继续保持 CERN-OHL-S-2.0：

```text
hardware/pcb/        KiCad / EasyEDA 源文件
hardware/enclosure/  STEP / STL / 尺寸图
hardware/drawings/   原理图、装配图、面板图
```

## 4. 复现步骤

1. 按 [hardware/BOM.csv](../hardware/BOM.csv) 采购模块；
2. 按 [hardware/WIRING.md](../hardware/WIRING.md) 接线；
3. 烧录 MicroPython 1.29 或兼容固件；
4. 执行：

```bat
python tools\deploy.py --port COM11
```

5. 配置 2.4GHz Wi-Fi；
6. 先空载测试继电器，再接水泵；
7. 完成 [hardware/WIRING.md](../hardware/WIRING.md) 的安全验收清单。

## 5. OSHW 对齐清单

- [x] 硬件设计源可获取（BOM、接线、装配）
- [x] 软件源代码可获取（MIT）
- [x] 允许修改和再分发
- [x] 说明电源、接地、感性负载和继电器安全
- [x] 明确第三方模块不纳入本仓库许可
- [x] 记录已知限制和未验证项
- [ ] OSHWA 认证 UID（未申请）
- [ ] 定制 PCB 源文件（当前无 PCB）
- [ ] 外壳 CAD（当前无外壳）

## 6. 安全与责任

硬件按 **“原样”** 提供，不附带任何担保。水泵、继电器、市电、电池和潮湿环境都有风险：

- 不要带电插拔接线；
- 水泵使用独立电源和续流二极管；
- 继电器使用 COM/NO，确保掉电释放；
- 继电器 IN 加硬件下拉；
- 不要用软件绕过 `max_run_s`、`min_off_s` 或故障锁存；
- 没有水位检测，禁止长时间无人值守运行；
- 涉及市电时必须有资质的电工处理。

## 7. 认证

如需 OSHWA 认证：

1. 准备完整设计源、BOM、装配说明和许可证；
2. 在 [Open Source Hardware Association](https://www.oshwa.org/) 提交申请；
3. 获得 OSHWA UID 后，才能使用 OSHWA 认证标志；
4. 在 README 中记录 UID。

本仓库当前**没有** OSHWA UID，也不会声称已认证。

## 8. 贡献

硬件贡献请附：

- 变更的接线/BOM；
- 电源和负载条件；
- 实测日志或照片（隐藏私人信息）；
- 安全验收结果；
- 许可证兼容性说明。

贡献默认按对应对象许可证授权：硬件源 CERN-OHL-S-2.0，软件 MIT。
