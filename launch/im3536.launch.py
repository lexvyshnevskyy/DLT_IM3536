import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    default_params_file = os.path.join(
        get_package_share_directory('im3536'),
        'config',
        'im3536.params.yaml',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params_file,
            description='Path to the YAML parameters file',
        ),
        Node(
            package='im3536',
            executable='im3536_node',
            name='im3536_node',
            output='screen',
            parameters=[LaunchConfiguration('params_file')],
        ),
    ])
