# Integration tests conftest: ensure imports resolve and load root tests conftest.
# This file is used when running with local config (tests/integration/pytest.ini),
# where pytest rootdir becomes tests/integration and relative imports may fail.

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
os.environ.update({
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5444",
    "POSTGRES_DB": "product_video_matching",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "dev",
    "POSTGRES_DSN": "postgresql://postgres:dev@localhost:5444/product_video_matching",
    "BUS_BROKER": "amqp://guest:guest@localhost:5672/",
    "VIDEO_CRAWLER_MODE": "live"
})

# Ensure the centralized config picks up the overrides by reloading after env update
import importlib
import types

# Import config module (libs/config.py) under top-level name 'config' and reload it
if "config" in sys.modules:
    importlib.reload(sys.modules["config"])
else:
    import config  # type: ignore
    importlib.reload(config)

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