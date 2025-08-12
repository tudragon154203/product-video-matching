from setuptools import setup, find_packages

setup(
    name="common-py",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "asyncpg>=0.29.0",
        "aio-pika>=9.3.1",
        "pydantic>=2.5.0",
        "structlog>=23.2.0",
    ],
)