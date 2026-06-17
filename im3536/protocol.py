from __future__ import annotations

import time
from typing import Optional

from .transport import Transport


class HiokiProtocol:
    """Hioki IM3536 SCPI-style command exchange."""

    def __init__(
        self,
        transport: Transport,
        *,
        terminator: str = 'crlf',
        query_timeout_sec: float = 2.0,
    ) -> None:
        self._transport = transport
        self._terminator = self._encode_terminator(terminator)
        self._query_timeout_sec = query_timeout_sec
        self._rx_buffer = bytearray()

    @staticmethod
    def _encode_terminator(terminator: str) -> bytes:
        normalized = terminator.strip().lower()
        if normalized in ('cr', 'cr_only'):
            return b'\r'
        if normalized in ('crlf', 'lf', 'cr+lf'):
            return b'\r\n'
        raise ValueError(f'Unsupported terminator "{terminator}". Use cr or crlf.')

    def write_command(self, command: str) -> int:
        payload = command.encode('ascii', errors='strict') + self._terminator
        return self._transport.write(payload)

    def read_line(self, timeout_sec: Optional[float] = None) -> Optional[str]:
        deadline = time.monotonic() + (timeout_sec if timeout_sec is not None else self._query_timeout_sec)
        while time.monotonic() < deadline:
            line = self._try_pop_line()
            if line is not None:
                return line
            self._rx_buffer.extend(self._transport.read_available())
            if not self._transport.is_open():
                return None
            time.sleep(0.01)
        return None

    def query(self, command: str, timeout_sec: Optional[float] = None) -> Optional[str]:
        self._rx_buffer.clear()
        if self.write_command(command) <= 0:
            return None
        return self.read_line(timeout_sec=timeout_sec)

    def _try_pop_line(self) -> Optional[str]:
        for ending in (b'\r\n', b'\r', b'\n'):
            idx = self._rx_buffer.find(ending)
            if idx < 0:
                continue
            raw = bytes(self._rx_buffer[:idx])
            del self._rx_buffer[:idx + len(ending)]
            line = raw.decode('ascii', errors='replace').strip()
            return line if line else None
        return None
