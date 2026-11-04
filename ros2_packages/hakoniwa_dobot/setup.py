from setuptools import find_packages, setup
setup(name='hakoniwa_dobot', version='0.1.0', packages=find_packages(),
      data_files=[('share/ament_index/resource_index/packages', ['resource/hakoniwa_dobot']),
                  ('share/hakoniwa_dobot', ['package.xml', 'README.md']),
                  ('share/hakoniwa_dobot/launch', ['launch/dobot.launch.py'])],
      install_requires=['setuptools'], zip_safe=True,
      maintainer='Hakoniwa contributors', maintainer_email='tmori@hakoniwa-lab.net',
      description='Dobot ROS service compatible Hakoniwa backend and launch wiring', license='Apache-2.0',
      entry_points={'console_scripts': ['configure = hakoniwa_dobot.configure:main', 'mirror = hakoniwa_dobot.mirror:main', 'jog = hakoniwa_dobot.jog:main']})
