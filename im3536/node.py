from __future__ import annotations

from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
from msgs.msg import Measurement

from .protocol import HiokiProtocol
from .transport import Transport, create_transport


class Im3536Node(Node):
    SUPPORTED_INTERFACES = ('rs232', 'usb', 'lan')

    def __init__(self) -> None:
        super().__init__('im3536_node')

        self.declare_parameter('interface', 'rs232')
        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 9600)
        self.declare_parameter('rtscts', False)
        self.declare_parameter('xonxoff', False)
        self.declare_parameter('host', '192.168.0.100')
        self.declare_parameter('lan_port', 23)
        self.declare_parameter('terminator', 'crlf')
        self.declare_parameter('query_timeout_sec', 2.0)
        self.declare_parameter('poll_period_sec', 0.5)
        self.declare_parameter('reconnect_period_sec', 2.0)
        self.declare_parameter('measure_command', ':MEASure?')
        self.declare_parameter('idn_command', '*IDN?')
        self.declare_parameter('query_on_connect', True)
        self.declare_parameter('source_name', 'im3536')
        self.declare_parameter('raw_topic', 'im3536/raw')
        self.declare_parameter('measurement_topic', 'im3536/measurement')
        self.declare_parameter('connected_topic', 'im3536/connected')

        self._interface = str(self.get_parameter('interface').value).strip().lower()
        if self._interface not in self.SUPPORTED_INTERFACES:
            raise ValueError(
                f'interface must be one of {self.SUPPORTED_INTERFACES}, got "{self._interface}"'
            )

        self._port = str(self.get_parameter('port').value)
        self._baudrate = int(self.get_parameter('baudrate').value)
        self._rtscts = bool(self.get_parameter('rtscts').value)
        self._xonxoff = bool(self.get_parameter('xonxoff').value)
        self._host = str(self.get_parameter('host').value)
        self._lan_port = int(self.get_parameter('lan_port').value)
        self._terminator = str(self.get_parameter('terminator').value)
        self._query_timeout_sec = float(self.get_parameter('query_timeout_sec').value)
        self._poll_period = float(self.get_parameter('poll_period_sec').value)
        self._reconnect_period = float(self.get_parameter('reconnect_period_sec').value)
        self._measure_command = str(self.get_parameter('measure_command').value)
        self._idn_command = str(self.get_parameter('idn_command').value)
        self._query_on_connect = bool(self.get_parameter('query_on_connect').value)
        self._source_name = str(self.get_parameter('source_name').value)

        self._transport: Optional[Transport] = None
        self._protocol: Optional[HiokiProtocol] = None
        self._connected = False
        self._last_connect_attempt_ns = 0

        self._raw_pub = self.create_publisher(String, str(self.get_parameter('raw_topic').value), 50)
        self._measurement_pub = self.create_publisher(
            Measurement,
            str(self.get_parameter('measurement_topic').value),
            50,
        )
        self._connected_pub = self.create_publisher(
            Bool,
            str(self.get_parameter('connected_topic').value),
            10,
        )

        self.create_timer(self._poll_period, self._poll)
        self.get_logger().info(self._startup_message())

    def _startup_message(self) -> str:
        if self._interface == 'lan':
            return (
                f'im3536 node starting on LAN {self._host}:{self._lan_port} '
                f'(terminator={self._terminator})'
            )
        label = 'RS-232C' if self._interface == 'rs232' else 'USB'
        return (
            f'im3536 node starting on {label} {self._port} @ {self._baudrate} baud '
            f'(terminator={self._terminator})'
        )

    def _set_connected(self, connected: bool) -> None:
        if connected == self._connected:
            return
        self._connected = connected
        msg = Bool()
        msg.data = connected
        self._connected_pub.publish(msg)

    def _try_connect(self) -> None:
        now_ns = self.get_clock().now().nanoseconds
        if now_ns - self._last_connect_attempt_ns < int(self._reconnect_period * 1e9):
            return
        self._last_connect_attempt_ns = now_ns

        transport = create_transport(
            self._interface,
            port=self._port,
            baudrate=self._baudrate,
            rtscts=self._rtscts,
            xonxoff=self._xonxoff,
            host=self._host,
            lan_port=self._lan_port,
            timeout_sec=self._query_timeout_sec,
        )
        if not transport.open():
            self._close_transport()
            self.get_logger().warning(self._connect_failure_message())
            return

        protocol = HiokiProtocol(
            transport,
            terminator=self._terminator,
            query_timeout_sec=self._query_timeout_sec,
        )

        if self._query_on_connect:
            idn = protocol.query(self._idn_command)
            if not idn:
                transport.close()
                self.get_logger().warning(
                    f'Connected transport opened but no response to {self._idn_command!r}.'
                )
                return
            self.get_logger().info(f'Instrument identity: {idn}')

        self._transport = transport
        self._protocol = protocol
        self._set_connected(True)
        self.get_logger().info(self._connect_success_message())

    def _connect_failure_message(self) -> str:
        if self._interface == 'lan':
            return f'Unable to open LAN connection to {self._host}:{self._lan_port}.'
        return f'Unable to open serial port {self._port}.'

    def _connect_success_message(self) -> str:
        if self._interface == 'lan':
            return f'Connected to IM3536 over LAN ({self._host}:{self._lan_port}).'
        label = 'RS-232C' if self._interface == 'rs232' else 'USB'
        return f'Connected to IM3536 over {label} ({self._port}).'

    def _close_transport(self) -> None:
        if self._transport is not None:
            self._transport.close()
        self._transport = None
        self._protocol = None
        self._set_connected(False)

    def _poll(self) -> None:
        if self._protocol is None:
            self._try_connect()
            return

        if not self._transport or not self._transport.is_open():
            self.get_logger().warning('Transport closed; reconnecting.')
            self._close_transport()
            return

        response = self._protocol.query(self._measure_command)
        if response is None:
            self.get_logger().warning('Measurement query timed out; reconnecting.')
            self._close_transport()
            return

        raw_msg = String()
        raw_msg.data = response
        self._raw_pub.publish(raw_msg)

        measurement = self._parse_measurement(response)
        if measurement is not None:
            self._measurement_pub.publish(measurement)

    def _parse_measurement(self, response: str) -> Optional[Measurement]:
        parts = [part.strip() for part in response.split(',') if part.strip()]
        if not parts:
            return None

        value = self._first_float(parts)
        msg = Measurement()
        msg.stamp = self.get_clock().now().to_msg()
        msg.source = self._source_name
        msg.channel = 0
        msg.type = 'im3536'
        msg.value = float(value) if value is not None else 0.0
        msg.raw_code = 0
        msg.sensor_value = msg.value
        msg.fault = 0
        msg.valid = value is not None
        msg.raw_json = response
        return msg

    @staticmethod
    def _first_float(parts: list[str]) -> Optional[float]:
        for part in parts:
            try:
                return float(part)
            except ValueError:
                continue
        return None

    def destroy_node(self) -> bool:
        self._close_transport()
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = Im3536Node()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
