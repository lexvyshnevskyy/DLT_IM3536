# im3536

Hioki IM3536 / IM3536-01 LCR meter driver. Publishes **`msgs/E720`** on `/im3536` (same contract as `measure_device`).

Configure the active interface on the instrument SYSTEM screen (baud rate, terminator, LAN IP/port).

## Interfaces

| `interface` | Connection | Linux device / address |
|-------------|------------|----------------------|
| `rs232` | D-sub RS-232C (crossover cable, e.g. Hioki 9637) | `/dev/ttyUSB0`, `/dev/ttyAMA0`, … |
| `usb` | USB Type-B virtual COM | `/dev/ttyACM0`, `/dev/ttyUSB0`, … |
| `lan` | TCP/IP (static IP on instrument) | `host` + `lan_port` params |

## System integration

Set impedance meter source in Web UI **Configuration → Impedance meter source** (`e720` or `im3536`), or in `/etc/default/delatometry`:

```bash
DELATOMETRY_MEASURE_SOURCE=im3536   # or e720
```

Core and Web UI subscribe to `/im3536` or `/measure_device` accordingly. Service: `delatometry-im3536.service`.

SCPI: `:MEASure?`, `:FREQuency?` → `E720.firstvalue`, `secondvalue`, `frequency`.

Topics: `/im3536` (E720), `im3536/raw`, `im3536/connected`.

**Full documentation:** [docs/en/hardware.md](../../docs/en/hardware.md) · [docs/uk/hardware.md](../../docs/uk/hardware.md)
