from __future__ import annotations

from typing import Any, Dict, Optional

from builtin_interfaces.msg import Time
from msgs.msg import E720
from std_msgs.msg import Float32, Header, String


def build_e720_message(
    *,
    stamp: Time,
    frame_id: str,
    data: Optional[Dict[str, Any]] = None,
    frequency_hz: float = 0.0,
) -> E720:
    payload = dict(data or {})
    if frequency_hz > 0.0:
        payload['Frequency'] = frequency_hz

    msg = E720()
    msg.header = Header()
    msg.header.stamp = stamp
    msg.header.frame_id = frame_id

    freq = float(payload.get('Frequency', 0.0) or 0.0)
    msg.offset = Float32(data=float(payload.get('OffSet', 0.0) or 0.0))
    msg.level = Float32(data=float(payload.get('Level', 0.0) or 0.0))
    msg.freq = Float32(data=freq)
    msg.freq10 = Float32(data=freq / 10.0 if freq else 0.0)
    msg.frequency = Float32(data=freq)
    msg.limit = String(data=str(payload.get('Limit', '')))
    msg.imparam = String(data=str(payload.get('ImParam', '')))
    msg.secparam = String(data=str(payload.get('SecParam', '')))
    msg.secvalue = Float32(data=float(payload.get('SecValue', 0.0) or 0.0))
    msg.secvalue10 = Float32(data=float(payload.get('SecValue10', 0.0) or 0.0))
    msg.secondvalue = Float32(data=float(payload.get('SecondValue', 0.0) or 0.0))
    msg.imvalue = Float32(data=float(payload.get('ImValue', 0.0) or 0.0))
    msg.imvalue10 = Float32(data=float(payload.get('ImValue10', 0.0) or 0.0))
    msg.firstvalue = Float32(data=float(payload.get('FirstValue', 0.0) or 0.0))
    msg.onchange = Float32(data=float(payload.get('OnChange', 0.0) or 0.0))
    msg.timestamp = Float32(data=float(payload.get('TimeStamp', 0.0) or 0.0))
    return msg
