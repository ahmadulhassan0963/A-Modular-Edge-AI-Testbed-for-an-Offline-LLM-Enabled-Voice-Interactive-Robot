from setuptools import find_packages, setup

package_name = 'voice_robot'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ahmad',
    maintainer_email='ahmad@todo.todo',
    description='Voice-controlled robot',
    license='MIT',
    entry_points={
        'console_scripts': [
            'voice_motor_node = voice_robot.voice_motor_node:main',
            'stt_node = voice_robot.stt_node:main',
            'tts_node = voice_robot.tts_node:main',
            'conversation_node = voice_robot.conversation_node:main',
            'narration_node = voice_robot.narration_node:main',
        ],
    },
)
