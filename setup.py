from glob import glob
from setuptools import find_packages, setup

package_name = 'im3536'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools', 'pyserial'],
    zip_safe=False,
    maintainer='Oleksii Vyshnevskyi',
    maintainer_email='lex.vyshnevskyy@gmail.com',
    description='ROS 2 driver node for the Hioki IM3536 LCR meter (RS-232C, USB, LAN).',
    license='MIT',
    entry_points={
        'console_scripts': [
            'im3536_node = im3536.node:main',
        ],
    },
)
