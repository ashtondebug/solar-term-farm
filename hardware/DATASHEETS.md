# 第三方器件与 datasheet

> OSHWA 认证要求第三方器件具有可公开获取的资料，且无需 NDA。以下为本项目使用的模块级器件。购买/替代器件时请确认 datasheet 版本与封装一致。

| 器件 | 用途 | 资料 | 备注 |
|---|---|---|---|
| Espressif ESP32-S3 | 主控 | [ESP32-S3 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf) | N16R8 模块；官方资料 |
| Ilitek ILI9341 | 2.8" TFT 控制器 | [ILI9341 datasheet](https://cdn-shop.adafruit.com/datasheets/ILI9341.pdf) | 240×320 SPI |
| Sensirion SHT31 | 温湿度 | [SHT3x datasheet](https://sensirion.com/media/documents/213E6A3B/63A5A569/Datasheet_SHT3x_DIS.pdf) | I²C，3.3V |
| ROHM BH1750FVI | 光照 | [BH1750FVI datasheet](https://fscdn.rohm.com/en/products/databook/datasheet/ic/sensor/light/bh1750fvi-e.pdf) | I²C，3.3V |
| HW-390 | 电容式土壤湿度 | [HW-390 module documentation](https://www.handsontec.com/dataspecs/module/Soil%20Moisture%20Sensor.pdf) | 模拟输出；模块级资料 |
| SRD-05VDC-SL-C 类继电器 | 泵开关 | [SRD relay datasheet](https://www.circuitbasics.com/wp-content/uploads/2015/11/SRD-05VDC-SL-C-Datasheet.pdf) | 实际模块以购入型号为准 |
| 低压直流水泵 | 执行器 | 购买型号的 datasheet/铭牌 | 泵型号由使用者选择，必须附公开资料 |

## 说明

- 第三方模块的版权/专利/商标仍归各自厂商；本仓库的 CERN-OHL-S-2.0 不覆盖这些模块。
- 不要求第三方器件开源；要求资料可访问、无需 NDA。
- 若使用不同型号，请更新本表并重新评估供电、继电器触点和泵电流。
- 链接失效时，优先使用厂商官网的 datasheet 页面，并记录版本号。
