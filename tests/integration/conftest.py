# Integration tests conftest: ensure imports resolve and load root tests conftest.
# This file is used when running with local config (tests/integration/pytest.ini),
# where pytest rootdir becomes tests/integration and relative imports may fail.


import importlib
import os
import sys
from pathlib import Path
import importlib.util
import socket
import time
import subprocess
import shutil
from urllib.parse import urlparse
import pytest

# Compute important paths
INTEGRATION_DIR = Path(__file__).resolve().parent          # tests/integration
TESTS_DIR = INTEGRATION_DIR.parent                         # tests
WORKSPACE_ROOT = TESTS_DIR.parent                          # project root
LIBS_DIR = WORKSPACE_ROOT / "libs"
COMMON_PY_DIR = LIBS_DIR / "common-py"
INFRA_DIR = WORKSPACE_ROOT / "infra"

# Add required paths to sys.path for module resolution (e.g., 'support', 'common_py', 'config')
for p in (COMMON_PY_DIR, LIBS_DIR, INFRA_DIR, WORKSPACE_ROOT, TESTS_DIR, INTEGRATION_DIR):
    ps = str(p)
    if ps not in sys.path:
        sys.path.append(ps)

# Propagate to PYTHONPATH so any subprocesses inherit resolution
pythonpath = os.environ.get("PYTHONPATH", "")
paths = [str(COMMON_PY_DIR), str(LIBS_DIR), str(TESTS_DIR), str(WORKSPACE_ROOT)]
merged = os.pathsep.join([p for p in paths + pythonpath.split(os.pathsep) if p])
os.environ["PYTHONPATH"] = merged

# Ensure integration test env overrides for host-run tests.
# Explicitly set to avoid fallback to Docker service names like 'postgres' or 'rabbitmq'
# ENFORCE REAL SERVICE USAGE - No mocks allowed in integration tests
os.environ.update({
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5444",
    "POSTGRES_DB": "product_video_matching",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "dev",
    "POSTGRES_DSN": "postgresql://postgres:dev@localhost:5444/product_video_matching",
    "BUS_BROKER": "amqp://guest:guest@localhost:5672/",
    "VIDEO_CRAWLER_MODE": "live",  # ENFORCE: Real video crawling, no mock mode
    "DROPSHIP_PRODUCT_FINDER_MODE": "live",  # ENFORCE: Real product finding, no mock mode
    "INTEGRATION_TESTS_ENFORCE_REAL_SERVICES": "true"  # ENFORCE: Flag to prevent mock fallbacks
})

# Auto-start infra (no build) if core ports are not reachable
def _is_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def _bus_host_port() -> tuple[str, int]:
    broker = os.environ.get("BUS_BROKER", "")
    parsed = urlparse(broker)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5672
    return host, int(port)

def _pg_host_port() -> tuple[str, int]:
    dsn = os.environ.get("POSTGRES_DSN", "")
    parsed = urlparse(dsn)
    host = parsed.hostname or os.environ.get("POSTGRES_HOST", "localhost")
    port = parsed.port or int(os.environ.get("POSTGRES_PORT", "5444"))
    return host, int(port)

def _ensure_infra_running():
    bus_host, bus_port = _bus_host_port()
    pg_host, pg_port = _pg_host_port()

    bus_up = _is_port_open(bus_host, bus_port)
    pg_up = _is_port_open(pg_host, pg_port)

    if bus_up and pg_up:
        print(f"[integration] Infra detected: RabbitMQ {bus_host}:{bus_port}, Postgres {pg_host}:{pg_port}")
        return

    # Only auto-start if both are down to avoid disrupting partial local setups
    if not bus_up and not pg_up:
        compose_file = WORKSPACE_ROOT / "infra" / "pvm" / "docker-compose.dev.yml"
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
            result = subprocess.run(cmd, cwd=str(WORKSPACE_ROOT), capture_output=True, text=True, check=False)
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

        # Wait for ports to open (max ~120s)
        deadline = time.time() + 120
        while time.time() < deadline:
            bus_up = _is_port_open(bus_host, bus_port)
            pg_up = _is_port_open(pg_host, pg_port)
            if bus_up and pg_up:
                print(f"[integration] Infra ready: RabbitMQ {bus_host}:{bus_port}, Postgres {pg_host}:{pg_port}")
                break
            time.sleep(3)

        if not (bus_up and pg_up):
            pytest.fail(
                f"Infrastructure failed to become ready within 120s.\n"
                f"Check container logs and ports:\n"
                f"  RabbitMQ: {bus_host}:{bus_port}\n  Postgres: {pg_host}:{pg_port}\n"
                f"Use:\n  docker compose -f {compose_file} logs -f\n"
                "Resolve issues, then re-run pytest."
            )
    else:
        # One of the services down; provide explicit guidance rather than auto-start to avoid conflicts
        missing = []
        if not bus_up:
            missing.append(f"RabbitMQ at {bus_host}:{bus_port}")
        if not pg_up:
            missing.append(f"Postgres at {pg_host}:{pg_port}")
        compose_file = WORKSPACE_ROOT / "infra" / "pvm" / "docker-compose.dev.yml"
        pytest.fail(
            "Detected partial infra readiness:\n"
            f"  Missing: {', '.join(missing)}\n"
            "Please ensure all required services are running. You can start the dev stack using:\n"
            f"  docker compose -f {compose_file} up -d\n"
            "Then re-run pytest."
        )

_ensure_infra_running()

# Ensure the centralized config picks up the overrides by reloading after env update

# Import config module (libs/config.py) under top-level name 'config' and reload it
if "config" in sys.modules:
    importlib.reload(sys.modules["config"])
else:
    import config  # type: ignore
    importlib.reload(config)

# ENFORCEMENT: Validate real service configuration before running tests


def enforce_real_service_usage():
    """
    Validate that integration tests are configured to use real services, not mocks.
    Raises AssertionError if mock configurations are detected.
    """
    # Check video crawler mode
    video_crawler_mode = os.environ.get("VIDEO_CRAWLER_MODE", "").lower()
    if video_crawler_mode in ["mock", "test", "fake"]:
        raise AssertionError(
            f"VIDEO_CRAWLER_MODE is set to '{video_crawler_mode}'. "
            "Integration tests must use 'live' mode for real video crawling."
        )

    # Check dropship product finder mode
    dropship_mode = os.environ.get("DROPSHIP_PRODUCT_FINDER_MODE", "").lower()
    if dropship_mode in ["mock", "test", "fake"]:
        raise AssertionError(
            f"DROPSHIP_PRODUCT_FINDER_MODE is set to '{dropship_mode}'. "
            "Integration tests must use 'live' mode for real product finding."
        )

    # Check enforcement flag
    enforce_flag = os.environ.get("INTEGRATION_TESTS_ENFORCE_REAL_SERVICES", "").lower()
    if enforce_flag != "true":
        raise AssertionError(
            "INTEGRATION_TESTS_ENFORCE_REAL_SERVICES must be set to 'true' for integration tests. "
            "This ensures real services are used instead of mocks."
        )

    # Validate service URLs are real, not localhost mocks (unless intentionally testing local services)
    broker_url = os.environ.get("BUS_BROKER", "")
    if "mock" in broker_url.lower() or "test" in broker_url.lower():
        raise AssertionError(
            f"BUS_BROKER appears to be configured for mock usage: {broker_url}. "
            "Integration tests should use real message broker."
        )

    print("Real service configuration validated for integration tests")


# Run enforcement check immediately
enforce_real_service_usage()

# Dynamically load the root tests/conftest.py so fixtures are available under this collection root
root_conftest_path = TESTS_DIR / "conftest.py"
spec = importlib.util.spec_from_file_location("root_tests_conftest", str(root_conftest_path))
module = importlib.util.module_from_spec(spec)
sys.modules["root_tests_conftest"] = module
spec.loader.exec_module(module)

# Re-export all public names from root conftest into this module's globals
for name in dir(module):
    if not name.startswith("_"):
        globals()[name] = getattr(module, name)
