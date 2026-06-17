import rclpy
from rclpy.node import Node


class Im3536Node(Node):
    def __init__(self) -> None:
        super().__init__('im3536_node')
        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 9600)
        self.declare_parameter('measurement_topic', 'im3536/measurement')
        self.get_logger().info('im3536 node started (stub)')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = Im3536Node()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
