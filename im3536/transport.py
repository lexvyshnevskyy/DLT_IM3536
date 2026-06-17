from __future__ import annotations

import socket
from abc import ABC, abstractmethod
from typing import Optional

try:
    import serial  # type: ignore
    from serial import SerialException  # type: ignore
except ImportError:  # pragma: no cover
    serial = None
    SerialException = Exception


class Transport(ABC):
    @abstractmethod
    def open(self) -> bool:
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    @abstractmethod
    def is_open(self) -> bool:
        ...

    @abstractmethod
    def write(self, data: bytes) -> int:
        ...

    @abstractmethod
    def read_available(self) -> bytes:
        ...


class SerialTransport(Transport):
    """RS-232C or USB virtual-COM transport (pyserial)."""

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout_sec: float = 0.05,
        rtscts: bool = False,
        xonxoff: bool = False,
    ) -> None:
        self._port = port
        self._baudrate = baudrate
        self._timeout_sec = timeout_sec
        self._rtscts = rtscts
        self._xonxoff = xonxoff
        self._serial: Optional[serial.Serial] = None

    @property
    def port(self) -> str:
        return self._port

    def open(self) -> bool:
        if serial is None:
            return False
        self.close()
        try:
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self._timeout_sec,
                rtscts=self._rtscts,
                xonxoff=self._xonxoff,
            )
            return True
        except SerialException:
            self._serial = None
            return False

    def close(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

    def is_open(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def write(self, data: bytes) -> int:
        if not self.is_open():
            return 0
        return int(self._serial.write(data))

    def read_available(self) -> bytes:
        if not self.is_open():
            return b''
        waiting = int(self._serial.in_waiting)
        if waiting <= 0:
            return b''
        return bytes(self._serial.read(waiting))


class LanTransport(Transport):
    """LAN transport over TCP/IP (instrument must be configured on SYSTEM screen)."""

    def __init__(
        self,
        host: str,
        port: int = 23,
        timeout_sec: float = 2.0,
    ) -> None:
        self._host = host
        self._port = port
        self._timeout_sec = timeout_sec
        self._socket: Optional[socket.socket] = None

    @property
    def endpoint(self) -> str:
        return f'{self._host}:{self._port}'

    def open(self) -> bool:
        self.close()
        try:
            sock = socket.create_connection(
                (self._host, self._port),
                timeout=self._timeout_sec,
            )
            sock.settimeout(self._timeout_sec)
            self._socket = sock
            return True
        except OSError:
            self._socket = None
            return False

    def close(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    def is_open(self) -> bool:
        return self._socket is not None

    def write(self, data: bytes) -> int:
        if not self.is_open():
            return 0
        self._socket.sendall(data)
        return len(data)

    def read_available(self) -> bytes:
        if not self.is_open():
            return b''
        try:
            return self._socket.recv(4096)
        except socket.timeout:
            return b''
        except OSError:
            self.close()
            return b''


def create_transport(
    interface: str,
    *,
    port: str = '/dev/ttyUSB0',
    baudrate: int = 9600,
    rtscts: bool = False,
    xonxoff: bool = False,
    host: str = '192.168.0.100',
    lan_port: int = 23,
    timeout_sec: float = 2.0,
) -> Transport:
    normalized = interface.strip().lower()
    if normalized == 'rs232':
        return SerialTransport(
            port=port,
            baudrate=baudrate,
            timeout_sec=0.05,
            rtscts=rtscts,
            xonxoff=xonxoff,
        )
    if normalized == 'usb':
        return SerialTransport(
            port=port,
            baudrate=baudrate,
            timeout_sec=0.05,
            rtscts=False,
            xonxoff=False,
        )
    if normalized == 'lan':
        return LanTransport(host=host, port=lan_port, timeout_sec=timeout_sec)
    raise ValueError(f'Unsupported interface "{interface}". Use rs232, usb, or lan.')
