"""
Infrastructure bootstrap utilities for integration tests.

Detects whether core dependencies (RabbitMQ and Postgres) are reachable on the
configured host:port and, if both are down, starts the dev stack via Docker Compose
without rebuilding. Provides clear failure instructions when auto-start is not possible
or if only a subset of services is down.

Usage:
    from support.infra_bootstrap import ensure_infra_running
    ensure_infra_running(workspace_root)
"""

import os
import socket
import time
import subprocess
import shutil
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

import pytest


def is_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if TCP port is reachable on host within given timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def bus_host_port(env: dict | None = None) -> Tuple[str, int]:
    """Extract RabbitMQ host:port from BUS_BROKER."""
    env = env or os.environ
    broker = env.get("BUS_BROKER", "")
    parsed = urlparse(broker)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5672
    return host, int(port)


def pg_host_port(env: dict | None = None) -> Tuple[str, int]:
    """Extract Postgres host:port from POSTGRES_DSN or explicit overrides."""
    env = env or os.environ
    dsn = env.get("POSTGRES_DSN", "")
    parsed = urlparse(dsn) if dsn else None
    host = (parsed.hostname if parsed else None) or env.get("POSTGRES_HOST", "localhost")
    port = (parsed.port if parsed else None) or int(env.get("POSTGRES_PORT", "5444"))
    return host, int(port)


def ensure_infra_running(workspace_root: Path) -> None:
    """
    Ensure RabbitMQ and Postgres are reachable; if both are down, attempt to start
    the dev stack via Docker Compose (no build), then wait for readiness.

    If Docker is not available or compose fails to start, fail fast with clear instructions.
    If only a subset of services is down (partial infra), fail with guidance to start full stack.
    """
    bus_host, bus_port = bus_host_port()
    pg_host, pg_port = pg_host_port()

    bus_up = is_port_open(bus_host, bus_port)
    pg_up = is_port_open(pg_host, pg_port)

    if bus_up and pg_up:
        print(f"[integration] Infra detected: RabbitMQ {bus_host}:{bus_port}, Postgres {pg_host}:{pg_port}")
        return

    compose_file = workspace_root / "infra" / "pvm" / "docker-compose.dev.yml"

    # Only auto-start when both are down; avoid conflicts with custom/partial setups
    if not bus_up and not pg_up:
        cmd = ["docker", "compose", "-f", str(compose_file), "up", "-d"]
        if shutil.which("docker") is None:
            pytest.fail(
                f"Required infra not running and 'docker' not found in PATH.\n"
                f"Please start services manually:\n"
                f"  docker compose -f {compose_file} up -d\n"
                f"Ensure Postgres on {pg_host}:{pg_port} and RabbitMQ on {bus_host}:{bus_port} are reachable."
            )
        print(f"[integration] Starting infra via: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, cwd=str(workspace_root), capture_output=True, text=True, check=False)
            if result.returncode != 0:
                print("[integration] docker compose output:\n", result.stdout, "\n", result.stderr)
                pytest.fail(
                    "Failed to start infra using docker compose.\n"
                    f"Try running manually:\n  {' '.join(cmd)}\n"
                    "After services are healthy, re-run pytest."
                )
        except Exception as e:
            pytest.fail(
                f"Error invoking docker compose: {e}\n"
                f"Please run:\n  {' '.join(cmd)}\n"
                "Then re-run pytest."
            )

        # Wait for readiness (ports open), up to ~120 seconds
        deadline = time.time() + 120
        while time.time() < deadline:
            bus_up = is_port_open(bus_host, bus_port)
            pg_up = is_port_open(pg_host, pg_port)
            if bus_up and pg_up:
                print(f"[integration] Infra ready: RabbitMQ {bus_host}:{bus_port}, Postgres {pg_host}:{pg_port}")
                return
            time.sleep(3)

        pytest.fail(
            "Infrastructure failed to become ready within 120s.\n"
            f"Check container logs and ports:\n"
            f"  RabbitMQ: {bus_host}:{bus_port}\n"
            f"  Postgres: {pg_host}:{pg_port}\n"
            f"Use:\n  docker compose -f {compose_file} logs -f\n"
            "Resolve issues, then re-run pytest."
        )

    # Partial infra: one up, one down; do not auto-start to avoid conflicts
    missing = []
    if not bus_up:
        missing.append(f"RabbitMQ at {bus_host}:{bus_port}")
    if not pg_up:
        missing.append(f"Postgres at {pg_host}:{pg_port}")
    pytest.fail(
        "Detected partial infra readiness:\n"
        f"  Missing: {', '.join(missing)}\n"
        "Please ensure all required services are running. You can start the dev stack using:\n"
        f"  docker compose -f {compose_file} up -d\n"
        "Then re-run pytest."
    )
