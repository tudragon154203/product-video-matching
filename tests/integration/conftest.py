# Integration tests conftest: ensure imports resolve and load root tests conftest.
# This file is used when running with local config (tests/integration/pytest.ini),
# where pytest rootdir becomes tests/integration and relative imports may fail.

import types
import importlib
import os
import sys
from pathlib import Path
import importlib.util

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
