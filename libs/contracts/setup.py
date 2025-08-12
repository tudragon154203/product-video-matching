from setuptools import setup, find_packages

setup(
    name="contracts",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "jsonschema>=4.20.0",
        "pydantic>=2.5.0",
    ],
)