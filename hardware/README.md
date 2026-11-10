# SolarTerm Farm 硬件源文件

本目录是 SolarTerm Farm 的 **module-level open hardware** 设计源：BOM、接线、装配与安全约束。

> **许可证：** 本目录中的硬件设计文档与 BOM 使用 [CERN-OHL-S-2.0](../LICENSE-HARDWARE)。
> 固件与 Web 软件使用 [MIT](../LICENSE)。
> 第三方模块（ESP32-S3 开发板、TFT、传感器、继电器等）仍受各自厂商条款约束。

## 设计范围

SolarTerm Farm 不是定制 PCB，而是由现成模块组成的可复现硬件：

- ESP32-S3 N16R8 开发板
- 2.8 英寸 240×320 ILI9341 SPI TFT
- SHT31 温湿度、BH1750 光照、HW-390 土壤湿度
- GPIO41 高电平按钮
- 3.3V 高电平触发继电器 + 低压直流水泵

因此本仓库提供的是 **模块级设计源**：BOM、接线、装配、固件和测试。若后续制作定制 PCB，应把 KiCad/EasyEDA 源文件加入本目录，并继续保持 CERN-OHL-S-2.0。

## 文件

| 文件 | 内容 |
|---|---|
| [BOM.csv](BOM.csv) | 物料清单 |
| [SCHEMATIC.svg](SCHEMATIC.svg) | 模块级原理图（设计源） |
| [SCHEMATIC.md](SCHEMATIC.md) | 原理图网络表与说明 |
| [ASSEMBLY.svg](ASSEMBLY.svg) | 装配布局图 |
| [WIRING.md](WIRING.md) | 接线与装配步骤 |
| [DATASHEETS.md](DATASHEETS.md) | 第三方器件 datasheet 链接 |
| [../docs/GPIO_WIRING.md](../docs/GPIO_WIRING.md) | 引脚、继电器、传感器总线 |
| [../docs/HARDWARE.md](../docs/HARDWARE.md) | 硬件规格与限制 |
| [../docs/OPEN_HARDWARE.md](../docs/OPEN_HARDWARE.md) | OSHW 合规说明与许可证矩阵 |

## 安全

水泵与继电器是感性负载。构建前必须阅读：

- [../docs/OPEN_HARDWARE.md](../docs/OPEN_HARDWARE.md)
- [../docs/GPIO_WIRING.md](../docs/GPIO_WIRING.md)

不要把水泵电流经过 ESP32 的 3.3V 稳压器；继电器 IN 需要硬件下拉；水泵使用 COM/NO 常开触点。
