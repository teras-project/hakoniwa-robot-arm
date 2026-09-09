from setuptools import find_packages, setup


package_name = "hakoniwa_arm_samples"


setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="tmori",
    maintainer_email="tmori@hakoniwa-lab.net",
    description="Robot-independent ROS 2 samples for Hakoniwa robot arms.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "control = hakoniwa_arm_samples.control:main",
            "monitor = hakoniwa_arm_samples.monitor:main",
        ],
    },
)
