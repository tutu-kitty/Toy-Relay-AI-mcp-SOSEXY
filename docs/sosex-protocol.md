# SOSEXY BLE 协议文档

> Funf「啵啵贝」(SOSEXY) 智能玩具的蓝牙低功耗 (BLE) 控制协议。本仓库 (`toy-mcp`) 直接使用本协议；协议本身原始来源见 [`51enuxu/sosexy-ble-control`](https://github.com/51enuxu/sosexy-ble-control)，那里有完整的逆向过程、抓包方法和 HCI 层分析。

---

## 📡 BLE 连接信息

| 项 | 值 |
|---|---|
| **广播名称** | `SOSEXY` |
| **连接方式** | 标准 BLE GATT 连接 |
| **配对要求** | 无需配对（任何范围内设备可连）|
| **单连接限制** | 同一时间只能被一个客户端控制 |

### GATT 特征 UUID

| 类型 | UUID | 用途 |
|---|---|---|
| **Service**（包含下面两个 characteristic）| `0000ee01-0000-1000-8000-00805f9b34fb` | 主服务 |
| **Write Characteristic** | `0000ee03-0000-1000-8000-00805f9b34fb` | 发送控制命令 |
| **Notify Characteristic** | `0000ee02-0000-1000-8000-00805f9b34fb` | 接收设备响应 |

> 写命令的 Handle 通常为 `0x000C`（对应 UUID `0000ee03-...`）。

---

## 📦 数据帧格式（12 字节定长）

```
Byte:  [0]  [1]  [2]  [3]  [4]  [5]   [6]   [7]      [8]  [9]   [10]  [11]
Value: 0x01 0x01 0x00 0x02 0x00 MODE  0x11  INTENS   0x00 MODE2 0x11  0x01
                              ^^^^^         ^^^^^^^        ^^^^^
                              模式字节1      强度值         模式字节2
```

### 字段说明

| 字节 | 字段 | 类型 | 说明 |
|---|---|---|---|
| 0-4 | 帧头 | 固定 `01 01 00 02 00` | 不变 |
| 5 | Mode Byte 1 | 变量 | 马达类型第 1 字节 |
| 6 | Separator | 固定 `0x11` | 分隔符 |
| 7 | Intensity | 变量 | 强度 0-100 |
| 8 | Padding | 固定 `0x00` | 占位 |
| 9 | Mode Byte 2 | 变量 | 马达类型第 2 字节 |
| 10 | Separator | 固定 `0x11` | 分隔符 |
| 11 | 帧尾 | 固定 `0x01` | 结束 |

---

## 🎛️ 三种马达的模式字节

| 功能 | Mode Byte 1 (Byte 5) | Mode Byte 2 (Byte 9) |
|---|---|---|
| **吮吸 (Suction)** | `0x07` | `0x08` |
| **震动 (Vibration)** | `0x01` | `0x02` |
| **电流 (Electric)** | `0x03` | `0x04` |

**强度：**
- 范围：`0` - `100`（十进制 / 即 `0x00` - `0x64`）
- 设为 `0` = 停止该马达
- 三马达**独立控制**，可同时运行；写一条命令不影响其他马达状态

---

## 📝 实际数据包示例

### 吮吸 50%
```
HEX: 01 01 00 02 00 07 11 32 00 08 11 01
                模式字节1=0x07    模式字节2=0x08
                            强度=0x32 (=50)
```

### 震动 30%
```
HEX: 01 01 00 02 00 01 11 1E 00 02 11 01
                模式字节1=0x01    模式字节2=0x02
                            强度=0x1E (=30)
```

### 电流 20%
```
HEX: 01 01 00 02 00 03 11 14 00 04 11 01
                模式字节1=0x03    模式字节2=0x04
                            强度=0x14 (=20)
```

### 停止所有马达
分别发强度=0 的三条：
```
吮吸停止: 01 01 00 02 00 07 11 00 00 08 11 01
震动停止: 01 01 00 02 00 01 11 00 00 02 11 01
电流停止: 01 01 00 02 00 03 11 00 00 04 11 01
```

---

## 🛠️ Python 实现参考

### 帧构建

```python
def build_frame(mode_byte1: int, mode_byte2: int, intensity: int) -> bytes:
    """构建 SOSEXY 12 字节控制帧"""
    intensity = max(0, min(100, intensity))
    return bytes([
        0x01, 0x01, 0x00, 0x02, 0x00,  # 帧头
        mode_byte1,                     # 模式字节1
        0x11,                           # 分隔符
        intensity,                      # 强度 0-100
        0x00,                           # 填充
        mode_byte2,                     # 模式字节2
        0x11,                           # 分隔符
        0x01,                           # 帧尾
    ])

# 例子：震动 50%
frame = build_frame(0x01, 0x02, 50)
# → bytes.fromhex('0101000200050111 32 000201 01')
```

### 用 bleak 发送

```python
from bleak import BleakClient

WRITE_UUID = "0000ee03-0000-1000-8000-00805f9b34fb"

async def send_command(client: BleakClient, frame: bytes):
    await client.write_gatt_char(WRITE_UUID, frame, response=True)
```

---

## 🔐 安全注意事项

1. **本地无加密**：协议无加密层，任何 BLE 范围内的设备**均可连接并控制**
2. **无认证机制**：无配对码、无 PIN 验证——靠「同一时间单连接」天然限制
3. **攻击面**：在公共场合（如咖啡店）使用有被附近设备抢连/干扰的风险
4. **建议**：蓝牙开着时确保玩具**在自己物理控制下**；不要在陌生蓝牙环境同时连接

---

## 📚 参考

- 原始逆向仓库：[51enuxu/sosexy-ble-control](https://github.com/51enuxu/sosexy-ble-control)（含完整抓包 / 帧分析）
- [Bluetooth Core Specification v5.3](https://www.bluetooth.com/specifications/bluetooth-core-specification/)
- [GATT 规范](https://www.bluetooth.com/specifications/specs/generic-attribute-profile-1-1/)
- [bleak (Python BLE 库)](https://github.com/hbldh/bleak)