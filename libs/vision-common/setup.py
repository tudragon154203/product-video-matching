from setuptools import setup, find_packages

setup(
    name="vision-common",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "opencv-python>=4.8.1",
        "numpy>=1.24.3",
        "pillow>=10.1.0",
    ],
)