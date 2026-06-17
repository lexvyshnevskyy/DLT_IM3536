from __future__ import annotations

import time
from typing import Optional

import rclpy
from msgs.msg import E720
from rclpy.node import Node
from std_msgs.msg import Bool, String

from .e720_publish import build_e720_message
from .protocol import HiokiProtocol
from .scpi_parser import parse_frequency_response, parse_measure_response
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
        self.declare_parameter('publish_rate', 2.0)
        self.declare_parameter('reconnect_period_sec', 2.0)
        self.declare_parameter('offline_timeout_sec', 2.0)
        self.declare_parameter('offline_publish_period_sec', 1.0)
        self.declare_parameter('frequency_query_every', 5)
        self.declare_parameter('endpoint', 'im3536')
        self.declare_parameter('frame_id_ready', 'im3536_ready')
        self.declare_parameter('frame_id_offline', 'im3536_offline')
        self.declare_parameter('measure_command', ':MEASure?')
        self.declare_parameter('frequency_command', ':FREQuency?')
        self.declare_parameter('idn_command', '*IDN?')
        self.declare_parameter('query_on_connect', True)
        self.declare_parameter('raw_topic', 'im3536/raw')
        self.declare_parameter('connected_topic', 'im3536/connected')

        self._interface = str(self.get_parameter('interface').value).strip().lower()
        if self._interface not in self.SUPPORTED_INTERFACES:
            raise ValueError(
                f'interface must be one of {self.SUPPORTED_INTERFACES}, got "{self._interface}"'
            )

        endpoint = str(self.get_parameter('endpoint').value)
        self._endpoint = endpoint if endpoint.startswith('/') else f'/{endpoint}'
        self._port = str(self.get_parameter('port').value)
        self._baudrate = int(self.get_parameter('baudrate').value)
        self._rtscts = bool(self.get_parameter('rtscts').value)
        self._xonxoff = bool(self.get_parameter('xonxoff').value)
        self._host = str(self.get_parameter('host').value)
        self._lan_port = int(self.get_parameter('lan_port').value)
        self._terminator = str(self.get_parameter('terminator').value)
        self._query_timeout_sec = float(self.get_parameter('query_timeout_sec').value)
        self._reconnect_period = float(self.get_parameter('reconnect_period_sec').value)
        self._offline_timeout_sec = float(self.get_parameter('offline_timeout_sec').value)
        self._offline_publish_period_sec = float(self.get_parameter('offline_publish_period_sec').value)
        self._frequency_query_every = max(1, int(self.get_parameter('frequency_query_every').value))
        self._measure_command = str(self.get_parameter('measure_command').value)
        self._frequency_command = str(self.get_parameter('frequency_command').value)
        self._idn_command = str(self.get_parameter('idn_command').value)
        self._query_on_connect = bool(self.get_parameter('query_on_connect').value)
        self._frame_id_ready = str(self.get_parameter('frame_id_ready').value)
        self._frame_id_offline = str(self.get_parameter('frame_id_offline').value)
        publish_rate = float(self.get_parameter('publish_rate').value)

        self._transport: Optional[Transport] = None
        self._protocol: Optional[HiokiProtocol] = None
        self._connected = False
        self._last_connect_attempt_ns = 0
        self._last_valid_monotonic: Optional[float] = None
        self._last_offline_publish_monotonic = 0.0
        self._last_frequency_hz = 0.0
        self._poll_count = 0

        self._e720_pub = self.create_publisher(E720, self._endpoint, 10)
        self._raw_pub = self.create_publisher(String, str(self.get_parameter('raw_topic').value), 50)
        self._connected_pub = self.create_publisher(
            Bool,
            str(self.get_parameter('connected_topic').value),
            10,
        )

        period = 1.0 / publish_rate if publish_rate > 0.0 else 0.5
        self.create_timer(period, self._poll)
        self.get_logger().info(
            f'im3536 publisher: topic={self._endpoint}, rate={publish_rate} Hz, {self._startup_message()}'
        )

    def _startup_message(self) -> str:
        if self._interface == 'lan':
            return f'LAN {self._host}:{self._lan_port}, terminator={self._terminator}'
        label = 'RS-232C' if self._interface == 'rs232' else 'USB'
        return f'{label} {self._port} @ {self._baudrate} baud, terminator={self._terminator}'

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

    def _should_publish_offline(self) -> bool:
        now = time.monotonic()
        if self._last_valid_monotonic is not None:
            if now - self._last_valid_monotonic < self._offline_timeout_sec:
                return False
        if now - self._last_offline_publish_monotonic < self._offline_publish_period_sec:
            return False
        self._last_offline_publish_monotonic = now
        return True

    def _publish_offline(self) -> None:
        if not self._should_publish_offline():
            return
        self._e720_pub.publish(
            build_e720_message(
                stamp=self.get_clock().now().to_msg(),
                frame_id=self._frame_id_offline,
                data=None,
            )
        )

    def _poll(self) -> None:
        if self._protocol is None:
            self._try_connect()
            self._publish_offline()
            return

        if not self._transport or not self._transport.is_open():
            self.get_logger().warning('Transport closed; reconnecting.')
            self._close_transport()
            self._publish_offline()
            return

        self._poll_count += 1
        if self._poll_count % self._frequency_query_every == 0:
            freq_line = self._protocol.query(self._frequency_command)
            if freq_line:
                self._last_frequency_hz = parse_frequency_response(freq_line)

        response = self._protocol.query(self._measure_command)
        if response is None:
            self.get_logger().warning('Measurement query timed out; reconnecting.')
            self._close_transport()
            self._publish_offline()
            return

        raw_msg = String()
        raw_msg.data = response
        self._raw_pub.publish(raw_msg)

        parsed = parse_measure_response(response)
        self._last_valid_monotonic = time.monotonic()
        self._e720_pub.publish(
            build_e720_message(
                stamp=self.get_clock().now().to_msg(),
                frame_id=self._frame_id_ready,
                data=parsed,
                frequency_hz=self._last_frequency_hz,
            )
        )

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
