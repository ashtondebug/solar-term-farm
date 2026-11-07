# 淘晶驰 Wiki 阅读记录

记录时间：2026-11-07。只记录**实际打开并阅读**的页面；未读页面不得假装已读。

## 1. 已阅读

| 页面 | URL | 关键结论 |
|---|---|---|
| 资料中心首页 | http://wiki.tjc1688.com/index.html | 文档体系包含快速入门、调试、控件、指令集、系统变量、语法、返回数据、下载、FAQ；适用于 X5/X3/X2/K0/T1/T0 系列 |
| TJC3224T128_011R | http://wiki.tjc1688.com/product/new_datasheet/T1/TJC3224T128_011R.html | T1 系列，2.8 寸，电阻触摸，带铁框，分辨率 320×240 |
| TJC3224T128_011R_A01 | http://wiki.tjc1688.com/product/new_datasheet/T1/TJC3224T128_011R_A01.html | 同 2.8 寸 320×240 电阻触摸；标注「新 MCU 方案」；提供规格书与出厂工程下载 |
| 串口屏返回数据格式 | http://wiki.tjc1688.com/return/index.html | 返回数据以 `0xFF 0xFF 0xFF` 结束；`bkcmd` 默认 2（只返回错误）；列出 00/01/02/…/24、0x65、0x66、0x67、0x70、0x71、0x86、0x87、0x88、0x89、0xFD、0xFE 等返回码 |

## 2. 已确认的硬件事实

- 型号 `TJC3224T128_011R_A01`：2.8 英寸、320×240、电阻触摸、新 MCU。
- 出厂工程下载：`http://filedown.tjc1688.com/tjcwiki/factory_project/T1/TJC3224T128.HMI`（可作为 USART HMI 起点）。
- 返回值结束符：三个 `0xFF`。
- `bkcmd` 默认值 2：只返回指令执行错误；设为非 0 才会返回成功/失败通知。

## 3. 尚未阅读（实现前必须补读）

- 指令集：http://wiki.tjc1688.com/commands/index.html
- 系统变量：http://wiki.tjc1688.com/variables/index.html
- 书写语法：http://wiki.tjc1688.com/grammar/index.html
- 控件详解：http://wiki.tjc1688.com/widgets/index.html
- ESP32-S3 调试：http://wiki.tjc1688.com/debug/arduino/esp32s3.html
- 创建工程/字库/下载：`start/create_project/*`
- 波特率与主动解析配置：`QA/baudrate.html`

## 4. 约束

- 不得把 `.HMI` 工程文件描述为屏幕运行固件；它是上位机工程，需编译/下载生成运行文件。
- 不得编造指令、变量格式、控件属性或通信协议。
- 不得套用其他品牌串口屏协议。
- 未确认的波特率、电平、供电、字库 ID 一律写入「待核实」，不进入代码常量。
