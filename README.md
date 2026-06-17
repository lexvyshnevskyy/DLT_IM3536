# im3536

Hioki IM3536 / IM3536-01 LCR meter driver over **RS-232C**, **USB**, or **LAN**.

Configure the active interface on the instrument SYSTEM screen (baud rate, terminator, LAN IP/port).

## Interfaces

| `interface` | Connection | Linux device / address |
|-------------|------------|----------------------|
| `rs232` | D-sub RS-232C (crossover cable, e.g. Hioki 9637) | `/dev/ttyUSB0`, `/dev/ttyAMA0`, … |
| `usb` | USB Type-B virtual COM (Hioki USB driver or kernel cdc-acm) | `/dev/ttyACM0`, `/dev/ttyUSB0`, … |
| `lan` | TCP/IP (static IP on instrument; port 1024–65535) | `host` + `lan_port` params |

## Run

```bash
# RS-232C (default params)
ros2 launch im3536 im3536.launch.py

# USB virtual COM
ros2 launch im3536 im3536.launch.py interface:=usb port:=/dev/ttyACM0

# LAN
ros2 launch im3536 im3536.launch.py interface:=lan host:=192.168.1.50 lan_port:=23
```

Topics: `im3536/raw`, `im3536/measurement`, `im3536/connected`.

**Full documentation:** [docs/en/hardware.md](../../docs/en/hardware.md) · [docs/uk/hardware.md](../../docs/uk/hardware.md)
